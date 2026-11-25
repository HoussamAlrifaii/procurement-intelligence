"""Red-flag report: what an auditor should look at after each data refresh.

Sections (latest publication year unless stated otherwise):
  1. Buyers to review   - single-bid rate of 80%+ or 20+ points above their country (2019-2022)
  2. Riskiest tenders   - highest single-bid risk according to the model, with the main reasons
  3. Unusual prices     - tenders with an award far above the price model's calibrated range
  4. Changes            - buyers newly flagged since the previous report

Every flag is an indicator for review, not evidence of wrongdoing. The report
names public buyers, so it is written to data/red_flags/ and not committed.

Usage (after the pipeline, the feature tables and the trained models exist):
    python -m procurement.red_flags
"""
import json
from datetime import date

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

from procurement import config, features, price_features
from procurement.analysis import run_analysis
from procurement.explain import FEATURE_LABELS, shap_values
from procurement.price_train import predict_range, widen_range
from procurement.tools import cpv_division_names


# --- Selection rules (pure functions, tested without data or models) ------------------

def select_buyers_to_review(buyer_table, rate=config.BUYER_RATE_THRESHOLD, gap=config.BUYER_GAP_THRESHOLD):
    """Buyers with a very high single-bid rate or far above their own country."""
    flagged = buyer_table[(buyer_table["single_bid_rate"] >= rate) | (buyer_table["gap_vs_country"] >= gap)]
    return flagged.sort_values(["single_bid_rate", "labelled_awards"], ascending=False)


def top_reasons(contributions, count=3):
    """The features that raised the risk most for one award, e.g. 'Country, Buyer's earlier single-bid rate'."""
    raising = contributions[contributions > 0].sort_values(ascending=False).head(count)
    return ", ".join(FEATURE_LABELS.get(name, name) for name in raising.index)


def rank_unusual_prices(frame, predicted_range, factor=config.PRICE_ANOMALY_FACTOR):
    """Awards more than `factor` times above the 90th percentile, largest excess first."""
    ratio = np.exp(frame[price_features.TARGET].to_numpy() - predicted_range["log_p90"].to_numpy())
    result = frame.assign(
        award_value_eur=np.exp(frame[price_features.TARGET]),
        expected_high_eur=np.exp(predicted_range["log_p90"]),
        times_above_range=ratio,
    )
    flagged = result[result["times_above_range"] > factor]
    return one_row_per_tender(flagged, "times_above_range")


def compare_with_previous(previous, current):
    """Buyers flagged now that were not flagged in the previous report."""
    if previous is None:
        return None
    return sorted(set(current["flagged_buyers"]) - set(previous["flagged_buyers"]))


# --- Scoring with the trained models ------------------------------------------------------

def load_booster(file_name):
    return lgb.Booster(model_file=str(config.MODELS_DIR / file_name))


def latest_year(frame):
    return frame[frame["publication_year"] == frame["publication_year"].max()]


def one_row_per_tender(frame, column):
    """Lots of one notice usually share their scores; keep the highest-scoring lot of each notice."""
    return frame.sort_values(column, ascending=False).drop_duplicates("notice_id")


def riskiest_awards(frame, model, top=config.RED_FLAGS_TOP):
    risk = model.predict(frame[features.FEATURES])
    scored = one_row_per_tender(frame.assign(single_bid_risk=risk), "single_bid_risk")
    top_rows = scored.head(top)
    values, _ = shap_values(model, top_rows)
    reasons = [top_reasons(values.loc[index]) for index in top_rows.index]
    return top_rows.assign(main_reasons=reasons)


def unusual_prices(frame, models, margin):
    predicted = widen_range(predict_range(models, frame), margin)
    return rank_unusual_prices(frame, predicted)


def buyer_names(connection, buyer_keys):
    keys = ", ".join(str(int(key)) for key in set(buyer_keys))
    if not keys:
        return {}
    rows = connection.sql(f"SELECT buyer_key, buyer_name FROM dim_buyer WHERE buyer_key IN ({keys})").fetchall()
    return dict(rows)


# --- Report -----------------------------------------------------------------------

def markdown_table(frame, columns):
    """Small Markdown table writer (avoids an extra dependency for DataFrame.to_markdown)."""
    header = "| " + " | ".join(columns.values()) + " |"
    divider = "|" + "---|" * len(columns)
    rows = ["| " + " | ".join(str(row[column]) for column in columns) + " |" for _, row in frame.iterrows()]
    return "\n".join([header, divider] + rows)


def write_report(buyers, risky, prices, low_price_count, new_buyers, year, path=config.RED_FLAGS_REPORT_PATH):
    divisions = cpv_division_names()
    risky = risky.assign(
        risk=risky["single_bid_risk"].map("{:.0%}".format),
        sector=risky["cpv_division"].astype(str).map(lambda code: f"{code} {divisions.get(code, '')}"[:45]),
        outcome=risky[features.TARGET].map({1: "single bid", 0: "2+ bids"}),
    )
    prices = prices.head(config.RED_FLAGS_TOP).assign(
        award=prices["award_value_eur"].map("EUR {:,.0f}".format),
        high_end=prices["expected_high_eur"].map("EUR {:,.0f}".format),
        times=prices["times_above_range"].map("{:.1f}x".format),
    )
    buyers = buyers.assign(rate=buyers["single_bid_rate"].map("{:.0%}".format),
                           gap=buyers["gap_vs_country"].map("{:+.0%}".format))

    lines = [
        f"# Red-flag report ({date.today():%d %B %Y})",
        "",
        "Indicators for review, not evidence of wrongdoing: a single bid or an unusual price can have "
        "legitimate causes (niche markets, urgency, data-entry errors).",
        "",
        "## Summary",
        "",
        f"- Buyers to review (2019-2022): **{len(buyers):,}**",
        f"- Awards scored for single-bid risk ({year}): top {len(risky)} listed below",
        f"- Tenders with an award far above the expected price range ({year}): **{len(prices):,}** "
        f"(top {min(len(prices), config.RED_FLAGS_TOP)} listed); awards far below it: {low_price_count:,} "
        "(often data-entry errors)",
    ]
    if new_buyers is not None:
        lines.append(f"- Buyers newly flagged since the previous report: **{len(new_buyers):,}**")
    lines += [
        "",
        "## 1. Buyers to review",
        "",
        f"At least 100 labelled competitive awards and a single-bid rate of "
        f"{config.BUYER_RATE_THRESHOLD:.0%}+ or {config.BUYER_GAP_THRESHOLD:.0%} points above their country.",
        "",
        markdown_table(buyers.head(config.RED_FLAGS_TOP), {
            "buyer_name": "Buyer", "country": "Country", "labelled_awards": "Awards",
            "rate": "Single-bid rate", "gap": "Vs country"}),
        "",
        f"## 2. Riskiest tenders ({year})",
        "",
        "Highest single-bid risk from the model (one row per tender), which only uses information known "
        "before publication; the outcome column shows what actually happened.",
        "",
        markdown_table(risky, {"buyer": "Buyer", "buyer_country": "Country", "sector": "Sector",
                               "risk": "Risk", "main_reasons": "Main reasons", "outcome": "Outcome"}),
        "",
        f"## 3. Tenders with an award far above the expected price ({year})",
        "",
        f"Award value more than {config.PRICE_ANOMALY_FACTOR:.0f} times the high end of the calibrated 80% range.",
        "",
        markdown_table(prices, {"buyer": "Buyer", "buyer_country": "Country", "cpv_group": "CPV group",
                                "award": "Award", "high_end": "Expected high end", "times": "Above range"}),
    ]
    if new_buyers:
        lines += ["", "## 4. Newly flagged buyers", ""] + [f"- {name}" for name in new_buyers]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main():
    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        buyers = select_buyers_to_review(run_analysis(connection, "02_buyer_red_flags"))

        bid_frame = latest_year(features.load_features())
        risky = riskiest_awards(bid_frame, load_booster("single_bid_lightgbm.txt"))

        price_frame = latest_year(price_features.load_price_features())
        price_models = {quantile: load_booster(f"price_p{quantile * 100:.0f}.txt") for quantile in config.PRICE_QUANTILES}
        margin = json.loads(config.PRICE_METRICS_PATH.read_text(encoding="utf-8"))["conformal_margin_log"]
        predicted = widen_range(predict_range(price_models, price_frame), margin)
        prices = rank_unusual_prices(price_frame, predicted)
        low_count = int((price_frame[price_features.TARGET].to_numpy()
                         < predicted["log_p10"].to_numpy() - np.log(config.PRICE_ANOMALY_FACTOR)).sum())

        names = buyer_names(connection, list(risky["buyer_key"]) + list(prices.head(config.RED_FLAGS_TOP)["buyer_key"]))
    risky = risky.assign(buyer=risky["buyer_key"].map(names))
    prices = prices.assign(buyer=prices["buyer_key"].map(names))

    snapshot = {"date": f"{date.today()}", "flagged_buyers": sorted(buyers["buyer_name"].astype(str))}
    previous = None
    if config.RED_FLAGS_SNAPSHOT_PATH.exists():
        previous = json.loads(config.RED_FLAGS_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    new_buyers = compare_with_previous(previous, snapshot)

    year = int(bid_frame["publication_year"].max())
    path = write_report(buyers, risky, prices, low_count, new_buyers, year)
    config.RED_FLAGS_SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {len(buyers):,} buyers to review, {len(prices):,} awards far above range -> "
          f"{path.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
