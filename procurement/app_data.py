"""Load the app bundle: download it if needed and expose it to the tools.

The tools query tables named ted_awards, fact_award and dim_buyer and read the
models from config.MODELS_DIR. Here those names become views over the bundle's
Parquet files, and MODELS_DIR points to the bundle's models, so the web app and
the API run the same tested tools as the command-line assistant.
"""
import io
import zipfile

import duckdb
import requests

from procurement import config
from procurement.sql_runner import sql_string


def bundle_dir():
    return config.APP_BUNDLE_DIR / config.APP_BUNDLE_NAME


def download_bundle(url=config.APP_BUNDLE_URL, target=None):
    """Download and unzip the bundle (about 90 MB) unless it is already there."""
    target = target or bundle_dir()
    if (target / "awards.parquet").exists():
        return target
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(target)
    return target


def connect(folder=None):
    """In-memory DuckDB with the bundle's tables as views; also points the tools to its models."""
    folder = folder or download_bundle()
    config.MODELS_DIR = folder / "models"
    connection = duckdb.connect()
    awards = sql_string(folder / "awards.parquet")
    connection.sql(f"CREATE VIEW ted_awards AS SELECT * FROM read_parquet({awards})")
    connection.sql(f"CREATE VIEW fact_award AS SELECT award_id, buyer_key FROM read_parquet({awards})")
    connection.sql(f"CREATE VIEW dim_buyer AS SELECT * FROM read_parquet({sql_string(folder / 'dim_buyer.parquet')})")
    return connection
