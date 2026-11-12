"""Central project settings. Every path and data source used in the project is defined here."""
from pathlib import Path

# Paths are built from this file's location rather than the current working
# directory, so scripts, notebooks and CI resolve the same locations no matter
# where they are launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"              # downloaded source files, never edited by hand
PROCESSED_DATA_DIR = DATA_DIR / "processed"  # files produced by the pipeline
DATABASE_PATH = DATA_DIR / "procurement.duckdb"

TED_RAW_DIR = RAW_DATA_DIR / "ted"
WORLD_BANK_RAW_DIR = RAW_DATA_DIR / "world_bank"
MANIFEST_PATH = RAW_DATA_DIR / "manifest.json"  # what was downloaded, when, and its fingerprint

SQL_DIR = PROJECT_ROOT / "sql"
LOAD_SQL_DIR = SQL_DIR / "load"
QUALITY_SQL_DIR = SQL_DIR / "quality"
PROFILE_SQL_DIR = SQL_DIR / "profile"
CLEAN_SQL_DIR = SQL_DIR / "clean"

REFERENCE_DIR = PROJECT_ROOT / "reference"      # small lookup tables committed to the repository
CPV_DIVISIONS_PATH = REFERENCE_DIR / "cpv_divisions.csv"

REPORTS_DIR = PROJECT_ROOT / "reports"
PROFILE_REPORT_PATH = REPORTS_DIR / "data_profile.md"

# Folders that must exist before the pipeline runs.
REQUIRED_FOLDERS = [RAW_DATA_DIR, PROCESSED_DATA_DIR, SQL_DIR, REPORTS_DIR]

# Python version the project is developed and tested against.
MINIMUM_PYTHON = (3, 12)

# --- Data sources -----------------------------------------------------------

# TED (Tenders Electronic Daily) contract award notices, one zipped CSV per
# publication year, from the EU open data portal (dataset "ted-csv").
TED_URL_TEMPLATE = "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-{year}.zip"

# World Bank "Contract Awards in Investment Project Financing (Since FY 2020)".
# This is a live file that the World Bank updates regularly, so the manifest
# records the download date and a SHA-256 fingerprint of the exact copy used.
WORLD_BANK_URL = (
    "https://financesonefiles.worldbank.org/f-one/DS00005/RS00005/"
    "Contract_Awards_in_Investment_Project_Financing__Since_FY_2020_.csv"
)
WORLD_BANK_FILE_NAME = "world_bank_contract_awards.csv"

# 2019-2022: recent years in the stable TED CSV format, before the 2023 switch
# to eForms notices changed how award data is published.
DEFAULT_YEARS = [2019, 2020, 2021, 2022]

# DuckDB view names: raw layer (text, as published) and clean layer (typed, cleaned).
TED_TABLE = "raw_ted_awards"
WORLD_BANK_TABLE = "raw_world_bank_awards"
TED_CLEAN_VIEW = "ted_awards"
WORLD_BANK_CLEAN_VIEW = "world_bank_awards"

TED_CLEAN_PATH = PROCESSED_DATA_DIR / "ted_awards_clean.parquet"
WORLD_BANK_CLEAN_PATH = PROCESSED_DATA_DIR / "world_bank_awards_clean.parquet"
