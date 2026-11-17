"""Feature table and time-based split for the single-bid risk model.

Usage (after the star schema exists):
    python -m procurement.features
"""
import duckdb
import pandas as pd

from procurement import config
from procurement.sql_runner import run_sql_file, sql_string

TARGET = "is_single_bid"

CATEGORICAL_FEATURES = [
    "buyer_country",
    "buyer_type",
    "buyer_main_activity",
    "contract_type",
    "procedure_type",
    "award_criterion",
    "cpv_division",
]

NUMERIC_FEATURES = [
    "is_framework_agreement",
    "is_eu_funded",
    "is_gpa_covered",
    "used_electronic_auction",
    "lots_in_notice",
    "log_estimated_value",
    "publication_month",
    "buyer_prior_awards",
    "buyer_prior_single_bid_rate",
]

FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# Known only after bidding closes. A test checks that none of them is a feature.
POST_PUBLICATION_COLUMNS = [
    "number_offers",
    "number_offers_raw",
    "number_offers_from_sme",
    "award_value_eur",
    "award_date",
    "winner_name",
    "winner_name_std",
    "winner_country",
    "winner_is_sme",
    "winner_count",
    "vendor_key",
]


def build_feature_table(connection, output_path=None):
    """Write the single-bid feature table to Parquet and return its row count."""
    output_path = output_path or config.SINGLE_BID_FEATURES_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_sql_file(
        connection,
        config.ML_SQL_DIR / "01_single_bid_features.sql",
        output_path=sql_string(output_path),
        train_end_year=config.TRAIN_END_YEAR,
        history_lag_days=config.BUYER_HISTORY_LAG_DAYS,
        smoothing_awards=config.BUYER_HISTORY_SMOOTHING,
    )
    return connection.sql(f"SELECT COUNT(*) FROM read_parquet({sql_string(output_path)})").fetchone()[0]


def load_features(path=None):
    """Read the feature table with categorical columns typed as pandas categories.

    LightGBM uses the category dtype to split on categories directly, without
    one-hot encoding.
    """
    frame = pd.read_parquet(path or config.SINGLE_BID_FEATURES_PATH)
    for column in CATEGORICAL_FEATURES:
        frame[column] = frame[column].astype("category")
    return frame


def split_by_year(frame):
    """Split into train / validation / test by publication year.

    A random split would let the model learn from 2022 tenders and be tested on
    2019 ones. Splitting by time matches how the model is used: trained on the
    past, applied to tenders that come next. All lots of one notice share a
    publication date, so a notice never ends up on both sides of a split.
    """
    year = frame["publication_year"]
    return {
        "train": frame[year <= config.TRAIN_END_YEAR],
        "validation": frame[year == config.VALIDATION_YEAR],
        "test": frame[year == config.TEST_YEAR],
    }


def main():
    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        rows = build_feature_table(connection)
    print(f"{config.SINGLE_BID_FEATURES_PATH.relative_to(config.PROJECT_ROOT)}: {rows:,} rows")


if __name__ == "__main__":
    main()
