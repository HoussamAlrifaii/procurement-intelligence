"""Build the data and model bundle used by the web app and the API.

The deployed app cannot run the pipeline or hold the full database, so this
script packs what the tools need into one zip file (about 90 MB):
  awards.parquet      awarded contracts 2021-2022, only the columns the tools use
  dim_buyer.parquet   display names of the buyers in those awards
  models/             the four LightGBM models and model_constants.json

Usage (after the pipeline and both training scripts):
    python -m procurement.app_bundle
Then upload data/app/procurement_app_bundle.zip to the GitHub Release "app-data-v1".
"""
import json
import shutil

import duckdb

from procurement import config
from procurement.sql_runner import sql_string
from procurement.tools import MODEL_CONSTANTS_FILE, training_price_margin, training_single_bid_rate

AWARD_COLUMNS = [
    "award_id", "notice_id", "publication_date", "cpv_code", "buyer_country", "award_status",
    "award_value_eur", "award_value_quality", "is_framework_agreement", "is_competitive_procedure",
    "is_single_bid", "winner_name", "winner_name_std", "winner_country", "winner_is_sme",
]
MODEL_FILES = ["single_bid_lightgbm.txt", "price_p10.txt", "price_p50.txt", "price_p90.txt"]


def export_data(connection, bundle_dir):
    columns = ", ".join(f"ted.{column}" for column in AWARD_COLUMNS)
    awards_path = bundle_dir / "awards.parquet"
    connection.sql(f"""
        COPY (
            SELECT {columns}, fact.buyer_key
            FROM ted_awards AS ted
            JOIN fact_award AS fact USING (award_id)
            WHERE ted.award_status = 'awarded'
              AND YEAR(ted.publication_date) BETWEEN {config.ASSISTANT_FIRST_YEAR} AND {config.ASSISTANT_LAST_YEAR}
        ) TO {sql_string(awards_path)} (FORMAT parquet, COMPRESSION zstd)
    """)
    connection.sql(f"""
        COPY (
            SELECT buyer_key, buyer_name, buyer_country
            FROM dim_buyer
            WHERE buyer_key IN (SELECT buyer_key FROM read_parquet({sql_string(awards_path)}))
        ) TO {sql_string(bundle_dir / "dim_buyer.parquet")} (FORMAT parquet, COMPRESSION zstd)
    """)


def copy_models(models_dir):
    models_dir.mkdir(parents=True, exist_ok=True)
    for file_name in MODEL_FILES:
        shutil.copy2(config.MODELS_DIR / file_name, models_dir / file_name)
    constants = {
        "training_single_bid_rate": training_single_bid_rate(),
        "price_conformal_margin_log": training_price_margin(),
    }
    (models_dir / MODEL_CONSTANTS_FILE).write_text(json.dumps(constants, indent=2), encoding="utf-8")


def build_bundle():
    bundle_dir = config.APP_BUNDLE_DIR / config.APP_BUNDLE_NAME
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        export_data(connection, bundle_dir)
    copy_models(bundle_dir / "models")

    archive = shutil.make_archive(str(bundle_dir), "zip", root_dir=bundle_dir)
    return bundle_dir, archive


def main():
    bundle_dir, archive = build_bundle()
    size_mb = sum(path.stat().st_size for path in bundle_dir.rglob("*") if path.is_file()) / 1e6
    print(f"Bundle folder: {bundle_dir.relative_to(config.PROJECT_ROOT)} ({size_mb:.0f} MB)")
    print(f"Zip to upload: {config.APP_BUNDLE_DIR.relative_to(config.PROJECT_ROOT)}/{config.APP_BUNDLE_NAME}.zip")


if __name__ == "__main__":
    main()
