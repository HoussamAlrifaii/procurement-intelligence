"""Tools the AI assistant can call. Every number in an answer comes from here.

  search_market   - SQL over the 2021-2022 awards: size, buyers, competitors, prices
  estimate_price  - fair price model: expected award value and calibrated 80% range
  single_bid_risk - single-bid risk model: probability of receiving only one offer

The LLM chooses the arguments; this module checks them, runs the query or the
model and returns plain dictionaries with numbers already formatted for display.
"""
import json
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


# --- Tools 2 and 3: the models ---------------------------------------------------

@lru_cache(maxsize=None)
def load_booster(file_name):
    return lgb.Booster(model_file=str(config.MODELS_DIR / file_name))


@lru_cache(maxsize=1)
def unknown_buyer_single_bid_rate():
    """Training-years single-bid rate: the smoothed history value of a buyer with no history."""
    sql = (f"SELECT AVG(is_single_bid) FROM read_parquet('{config.SINGLE_BID_FEATURES_PATH.as_posix()}') "
           f"WHERE publication_year <= {config.TRAIN_END_YEAR}")
    return duckdb.sql(sql).fetchone()[0]


@lru_cache(maxsize=1)
def price_conformal_margin():
    report = json.loads(config.PRICE_METRICS_PATH.read_text(encoding="utf-8"))
    return report["conformal_margin_log"]


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
    "estimated_value": {"type": "number", "description": "Buyer's published estimate in EUR, if known."},
    "lots": {"type": "integer", "description": "Number of lots in the tender (default 1)."},
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_market",
        "description": "Summarise a public procurement market from 2021-2022 EU contract awards: number of contracts, "
                       "top buyers, top winning companies, typical award values, single-bid rate and SME win share.",
        "parameters": {"type": "object", "required": ["cpv_groups"], "properties": {
            "cpv_groups": {"type": "array", "items": {"type": "string"},
                           "description": "CPV codes (2 to 5 leading digits) describing what the company sells, "
                                          "e.g. '45314' for telecommunications installation or '72' for IT services."},
            "country": {"type": "string", "description": "Two-letter buyer country code; omit for all countries."},
            "min_value": {"type": "number", "description": "Smallest award value in EUR to include."},
            "max_value": {"type": "number", "description": "Largest award value in EUR to include."},
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
