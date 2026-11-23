"""Tools the AI assistant can call. Every number in an answer comes from here.

  find_cpv_codes  - official CPV codes matching keywords, with how often buyers use them
  search_market   - SQL over the 2021-2022 awards: size, buyers, competitors, prices
  estimate_price  - fair price model: expected award value and calibrated 80% range
  single_bid_risk - single-bid risk model: probability of receiving only one offer

The LLM chooses the arguments; this module checks them, runs the query or the
model and returns plain dictionaries with numbers already formatted for display.
"""
import json
import math
import re
from functools import lru_cache

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

from procurement import config, features, price_features
from procurement.sql_runner import read_sql

CONTRACT_TYPES = ["Works", "Supplies", "Services"]


class ToolError(ValueError):
    """Invalid arguments; the message is sent back to the LLM so it can correct them."""


# --- Formatting ---------------------------------------------------------------

NOT_AVAILABLE = "not available"
SMALL_MARKET = 30   # fewer awards than this: suggest searching related codes too


def euros(value):
    return NOT_AVAILABLE if value is None or pd.isna(value) else f"EUR {value:,.0f}"


def percent(value):
    return NOT_AVAILABLE if value is None or pd.isna(value) else f"{value:.1%}"


def count(value):
    return f"{int(value):,}"


def short_name(name, limit=80):
    """Some official names carry whole addresses; keep answers readable."""
    return name if len(name) <= limit else name[:limit].rstrip() + "..."


# --- Argument checks ------------------------------------------------------------

@lru_cache(maxsize=1)
def cpv_code_names():
    """Official CPV list as {8-digit code: English name}; the check digit ('-1') is dropped."""
    table = pd.read_csv(config.CPV_CODES_PATH, dtype=str, encoding="utf-8-sig")
    codes = table["CODE"].str.split("-").str[0]
    return dict(zip(codes, table["EN"]))


def search_prefix(code):
    """'15810000' -> '1581': trailing zeros only pad the code, so the prefix selects the same awards."""
    return code.rstrip("0").ljust(2, "0")


def keyword_pattern(word):
    """Regex for one keyword in a CPV name.

    Long words are shortened so 'cabling' matches 'cable' and 'cleaning' matches 'clean',
    and must start a word ('bread' matches 'Bread products', not 'Breakdown').
    Words of up to 4 letters must match whole, plurals allowed ('bus' matches 'buses', not 'business').
    """
    if len(word) <= 4:
        return re.compile(rf"\b{re.escape(word)}(es|s)?\b")
    stem = word if len(word) <= 5 else word[:max(4, len(word) - 3)]
    return re.compile(rf"\b{re.escape(stem)}")


@lru_cache(maxsize=1)
def cpv_division_names():
    table = pd.read_csv(config.CPV_DIVISIONS_PATH, dtype=str)
    return dict(zip(table["cpv_division"], table["cpv_division_name"]))


def known_values(connection, sql):
    return {row[0] for row in connection.sql(sql).fetchall()}


def check_cpv_codes(connection, cpv_codes):
    """Keep 2 to 5 leading digits of each CPV code and reject prefixes absent from the data.

    More digits mean a more specific market: 45 construction work, 453 building
    installation work, 45314 installation of telecommunications equipment.
    """
    codes = {str(code).strip()[:5] for code in cpv_codes}
    codes = {code for code in codes if code}
    if not codes or any(len(code) < 2 or not code.isdigit() for code in codes):
        raise ToolError("Give CPV codes of 2 to 5 digits, e.g. '51', '453' or '45314'.")
    known = known_values(connection, """
        SELECT DISTINCT UNNEST([LEFT(cpv_code, 2), LEFT(cpv_code, 3), LEFT(cpv_code, 4), LEFT(cpv_code, 5)])
        FROM ted_awards WHERE cpv_code IS NOT NULL""")
    unknown = sorted(codes - known)
    if unknown:
        raise ToolError(f"Unknown CPV codes: {unknown}. Use codes that exist in the CPV list.")
    return sorted(codes)


def check_cpv_group(connection, cpv_code):
    """The models use the three-digit CPV group; longer codes are cut to it."""
    code = check_cpv_codes(connection, [cpv_code])[0]
    if len(code) < 3:
        raise ToolError("This tool needs a CPV code of at least three digits (e.g. '453'), not a division.")
    return code[:3]


def check_country(connection, country):
    if country is None:
        return None
    code = str(country).strip().upper()
    known = known_values(connection, "SELECT DISTINCT buyer_country FROM ted_awards")
    if code not in known:
        raise ToolError(f"Unknown country '{country}'. Use a two-letter code such as PL, DE or FR.")
    return code


def check_contract_type(contract_type):
    for option in CONTRACT_TYPES:
        if str(contract_type).strip().lower() == option.lower():
            return option
    raise ToolError(f"contract_type must be one of {CONTRACT_TYPES}.")


# --- Tool 1: market search ------------------------------------------------------

def search_market(connection, cpv_groups, country=None, min_value=None, max_value=None):
    """Who buys, who wins, at what price and with how much competition in a market."""
    parameters = {
        "cpv_codes": check_cpv_codes(connection, cpv_groups),
        "country": check_country(connection, country),
        "min_value": min_value,
        "max_value": max_value,
    }
    years = {"first_year": config.ASSISTANT_FIRST_YEAR, "last_year": config.ASSISTANT_LAST_YEAR}
    connection.execute(read_sql(config.ASSISTANT_SQL_DIR / "00_matching_awards.sql", **years), parameters)

    summary = connection.sql(read_sql(config.ASSISTANT_SQL_DIR / "01_market_summary.sql")).df().iloc[0]
    buyers = connection.sql(read_sql(config.ASSISTANT_SQL_DIR / "02_top_buyers.sql")).df()
    winners = connection.sql(read_sql(config.ASSISTANT_SQL_DIR / "03_top_winners.sql")).df()

    result = {
        "period": f"{config.ASSISTANT_FIRST_YEAR}-{config.ASSISTANT_LAST_YEAR}",
        "filters": parameters,
        "cpv_divisions": {code: cpv_division_names().get(code[:2], "unknown") for code in parameters["cpv_codes"]},
        "contracts_awarded": count(summary["awards"]),
        "tenders": count(summary["tenders"]),
        "buyers": count(summary["buyers"]),
        "winning_companies": count(summary["winners"]),
        "typical_award_value": euros(summary["median_value"]),
        "usual_value_range": (NOT_AVAILABLE if pd.isna(summary["p10_value"])
                              else f"{euros(summary['p10_value'])} to {euros(summary['p90_value'])}"),
        "single_bid_rate": percent(summary["single_bid_rate"]),
        "share_won_by_smes": percent(summary["sme_win_share"]),
        "top_buyers": [
            {"buyer": short_name(row.buyer), "country": row.country, "contracts": count(row.awards),
             "typical_value": euros(row.median_value)}
            for row in buyers.itertuples()
        ],
        "top_winners": [
            {"company": short_name(row.company), "country": row.country, "contracts": count(row.awards),
             "sme": bool(row.is_sme) if not pd.isna(row.is_sme) else None}
            for row in winners.itertuples()
        ],
    }
    if summary["awards"] < SMALL_MARKET:
        # Buyers code similar work differently (e.g. network projects as equipment or IT
        # services rather than installation), so a narrow code can miss most of a market.
        result["note"] = (f"Only {int(summary['awards'])} awards match. Search again with related or broader "
                          "codes (e.g. equipment and service codes next to installation codes) or wider filters.")
    return result


# --- Tool 2: CPV code lookup -------------------------------------------------------

def find_cpv_codes(connection, keywords, limit=10):
    """Official CPV codes whose English name matches the keywords, with their number of awards.

    Codes are ranked by the keywords they match (rare words weigh more, like TF-IDF),
    then by how many awards use them, so the codes buyers actually use come first.
    """
    patterns = [keyword_pattern(word) for word in re.findall(r"[a-z]{2,}", str(keywords).lower())]
    if not patterns:
        raise ToolError("Give one or more English keywords, e.g. 'bread' or 'network cabling'.")

    names = {code: name.lower() for code, name in cpv_code_names().items()}
    # Rare words say more than common ones: in "medical gloves", "gloves" should decide.
    weights = []
    for pattern in patterns:
        matching = sum(pattern.search(name) is not None for name in names.values())
        weights.append(math.log(len(names) / matching) if matching else 0.0)

    candidates = []
    for code, lowered in names.items():
        score = sum(weight for pattern, weight in zip(patterns, weights) if pattern.search(lowered))
        if score > 0:
            candidates.append((score, search_prefix(code), cpv_code_names()[code]))
    candidates.sort(key=lambda candidate: (-candidate[0], len(candidate[1])))
    candidates = candidates[:50]
    if not candidates:
        return {"keywords": keywords, "codes": [], "note": "No CPV names match; try other or broader words."}

    counts = dict(connection.execute(f"""
        SELECT prefix, COUNT(*)
        FROM ted_awards, UNNEST($prefixes) AS prefixes(prefix)
        WHERE ted_awards.award_status = 'awarded'
          AND YEAR(ted_awards.publication_date) BETWEEN {config.ASSISTANT_FIRST_YEAR} AND {config.ASSISTANT_LAST_YEAR}
          AND starts_with(ted_awards.cpv_code, prefix)
        GROUP BY prefix
    """, {"prefixes": [prefix for _, prefix, _ in candidates]}).fetchall())

    ranked = sorted(candidates, key=lambda candidate: (-round(candidate[0], 6), -counts.get(candidate[1], 0)))
    return {
        "keywords": keywords,
        "codes": [
            {"cpv_code": prefix, "name": name, "contracts_2021_2022": count(counts.get(prefix, 0))}
            for _, prefix, name in ranked[:limit]
        ],
    }


# --- Tools 3 and 4: the models ---------------------------------------------------

@lru_cache(maxsize=None)
def load_booster(file_name):
    return lgb.Booster(model_file=str(config.MODELS_DIR / file_name))


MODEL_CONSTANTS_FILE = "model_constants.json"


def training_single_bid_rate():
    """Single-bid rate of the training years, computed from the feature table."""
    sql = (f"SELECT AVG(is_single_bid) FROM read_parquet('{config.SINGLE_BID_FEATURES_PATH.as_posix()}') "
           f"WHERE publication_year <= {config.TRAIN_END_YEAR}")
    return duckdb.sql(sql).fetchone()[0]


def bundled_constant(name):
    """A value stored next to the models in the app bundle, or None when running from the pipeline."""
    constants_path = config.MODELS_DIR / MODEL_CONSTANTS_FILE
    if not constants_path.exists():
        return None
    return json.loads(constants_path.read_text(encoding="utf-8"))[name]


def training_price_margin():
    report = json.loads(config.PRICE_METRICS_PATH.read_text(encoding="utf-8"))
    return report["conformal_margin_log"]


@lru_cache(maxsize=1)
def unknown_buyer_single_bid_rate():
    """The smoothed history value of a buyer with no history (the training-years rate).

    The app bundle stores it next to the models, because the feature table is not deployed.
    """
    return bundled_constant("training_single_bid_rate") or training_single_bid_rate()


@lru_cache(maxsize=1)
def price_conformal_margin():
    """Calibration margin of the price range, stored with the models it belongs to."""
    return bundled_constant("price_conformal_margin_log") or training_price_margin()


def planned_tender(cpv_group, country, contract_type, estimated_value=None, lots=1):
    """One planned tender as model input. Details the user did not give take common
    defaults (open procedure, buyer type not reported, unknown buyer history)."""
    log_estimate = np.log(estimated_value) if estimated_value and 100 <= estimated_value < 1e9 else np.nan
    row = {
        "buyer_country": country,
        "buyer_type": "Not reported",
        "buyer_main_activity": "Not reported",
        "contract_type": contract_type,
        "procedure_type": "Open",
        "award_criterion": "Lowest price",
        "cpv_division": cpv_group[:2],
        "cpv_group": cpv_group,
        "is_framework_agreement": 0,
        "is_eu_funded": 0,
        "is_gpa_covered": 0,
        "used_electronic_auction": 0,
        "lots_in_notice": lots,
        "log_estimated_value": log_estimate,
        "publication_month": pd.Timestamp.today().month,
        "buyer_prior_awards": 0,
        "buyer_prior_single_bid_rate": unknown_buyer_single_bid_rate(),
        "buyer_prior_priced_awards": 0,
        "buyer_prior_mean_log_value": np.nan,
    }
    frame = pd.DataFrame([row])
    for column in set(features.CATEGORICAL_FEATURES) | set(price_features.CATEGORICAL_FEATURES):
        frame[column] = frame[column].astype("category")
    return frame


def checked_tender(connection, cpv_group, country, contract_type, estimated_value, lots):
    group = check_cpv_group(connection, cpv_group)
    return planned_tender(group, check_country(connection, country), check_contract_type(contract_type),
                          estimated_value, int(lots or 1))


def estimate_price(connection, cpv_group, country, contract_type, estimated_value=None, lots=1):
    """Expected award value and calibrated 80% range for one lot."""
    tender = checked_tender(connection, cpv_group, country, contract_type, estimated_value, lots)
    log_values = [load_booster(f"price_p{quantile * 100:.0f}.txt").predict(tender[price_features.FEATURES])[0]
                  for quantile in config.PRICE_QUANTILES]
    low, expected, high = sorted(log_values)
    margin = price_conformal_margin()
    return {
        "expected_award_value": euros(np.exp(expected)),
        "range_80_percent": f"{euros(np.exp(low - margin))} to {euros(np.exp(high + margin))}",
        "based_on_buyer_estimate": not np.isnan(tender["log_estimated_value"].iloc[0]),
        "note": "Typical error is about 26% with a buyer estimate and about 79% without one.",
    }


def single_bid_risk(connection, cpv_group, country, contract_type, estimated_value=None, lots=1):
    """Probability that a competitive tender like this one receives a single offer."""
    tender = checked_tender(connection, cpv_group, country, contract_type, estimated_value, lots)
    probability = load_booster("single_bid_lightgbm.txt").predict(tender[features.FEATURES])[0]
    return {
        "single_bid_risk": percent(probability),
        "average_risk_all_tenders": "30.9%",
        "note": "A risk indicator for the buyer's market, not a judgement on any buyer.",
    }


# --- What the LLM sees -----------------------------------------------------------

TENDER_PARAMETERS = {
    "cpv_group": {"type": "string", "description": "CPV code of at least three digits, e.g. '453' or '45314'."},
    "country": {"type": "string", "description": "Two-letter buyer country code, e.g. 'PL'."},
    "contract_type": {"type": "string", "enum": CONTRACT_TYPES},
    "estimated_value": {"type": ["number", "null"], "description": "Buyer's published estimate in EUR, if known."},
    "lots": {"type": ["integer", "null"], "description": "Number of lots in the tender (default 1)."},
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "find_cpv_codes",
        "description": "Look up official CPV codes by English keywords in their names (e.g. 'bread', 'cleaning', "
                       "'telecommunications installation'). Returns codes, names and how many 2021-2022 awards use "
                       "each code. Use it before searching when you are not sure which codes fit.",
        "parameters": {"type": "object", "required": ["keywords"], "properties": {
            "keywords": {"type": "string", "description": "One to three English words describing the product or service."},
        }},
    }},
    {"type": "function", "function": {
        "name": "search_market",
        "description": "Summarise a public procurement market from 2021-2022 EU contract awards: number of contracts, "
                       "top buyers, top winning companies, typical award values, single-bid rate and SME win share.",
        "parameters": {"type": "object", "required": ["cpv_groups"], "properties": {
            "cpv_groups": {"type": "array", "items": {"type": "string"},
                           "description": "CPV codes (2 to 5 leading digits) describing what the company sells, "
                                          "e.g. '45314' for telecommunications installation or '72' for IT services."},
            # Optional inputs also accept null: some models send null instead of leaving them out.
            "country": {"type": ["string", "null"], "description": "Two-letter buyer country code; null for all countries."},
            "min_value": {"type": ["number", "null"], "description": "Smallest award value in EUR to include."},
            "max_value": {"type": ["number", "null"], "description": "Largest award value in EUR to include."},
        }},
    }},
    {"type": "function", "function": {
        "name": "estimate_price",
        "description": "Predict the award value of one planned tender (lot): expected value and 80% range.",
        "parameters": {"type": "object", "required": ["cpv_group", "country", "contract_type"],
                       "properties": TENDER_PARAMETERS},
    }},
    {"type": "function", "function": {
        "name": "single_bid_risk",
        "description": "Predict the probability that one planned competitive tender receives only one offer.",
        "parameters": {"type": "object", "required": ["cpv_group", "country", "contract_type"],
                       "properties": TENDER_PARAMETERS},
    }},
]

TOOLS = {
    "find_cpv_codes": find_cpv_codes,
    "search_market": search_market,
    "estimate_price": estimate_price,
    "single_bid_risk": single_bid_risk,
}


def run_tool(connection, name, arguments):
    """Run one tool call. Problems are returned as {'error': ...} for the LLM to fix."""
    if name not in TOOLS:
        return {"error": f"Unknown tool '{name}'. Available: {sorted(TOOLS)}."}
    try:
        return TOOLS[name](connection, **arguments)
    except (ToolError, TypeError) as problem:
        return {"error": str(problem)}
