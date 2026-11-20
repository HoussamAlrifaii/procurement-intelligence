"""Feature table for the fair price model.

Usage (after the star schema exists):
    python -m procurement.price_features
"""
import duckdb
import pandas as pd

from procurement import config
from procurement.sql_runner import run_sql_file, sql_string

TARGET = "log_award_value"

CATEGORICAL_FEATURES = [
    "buyer_country",
    "buyer_type",
    "buyer_main_activity",
    "contract_type",
    "procedure_type",
    "award_criterion",
    "cpv_division",
    "cpv_group",
]

NUMERIC_FEATURES = [
    "is_eu_funded",
    "is_gpa_covered",
    "used_electronic_auction",
    "lots_in_notice",
    "log_estimated_value",
    "publication_month",
    "buyer_prior_priced_awards",
    "buyer_prior_mean_log_value",
]

FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# Used to report results separately; never a feature.
EVALUATION_COLUMNS = ["estimate_equals_award"]


def build_price_feature_table(connection, output_path=None):
    """Write the price feature table to Parquet and return its row count."""
    output_path = output_path or config.PRICE_FEATURES_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_sql_file(
        connection,
        config.ML_SQL_DIR / "02_price_features.sql",
        output_path=sql_string(output_path),
        history_lag_days=config.BUYER_HISTORY_LAG_DAYS,
    )
    return connection.sql(f"SELECT COUNT(*) FROM read_parquet({sql_string(output_path)})").fetchone()[0]


def load_price_features(path=None):
    frame = pd.read_parquet(path or config.PRICE_FEATURES_PATH)
    for column in CATEGORICAL_FEATURES:
        frame[column] = frame[column].astype("category")
    return frame


def main():
    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        rows = build_price_feature_table(connection)
    print(f"{config.PRICE_FEATURES_PATH.relative_to(config.PROJECT_ROOT)}: {rows:,} rows")


if __name__ == "__main__":
    main()
