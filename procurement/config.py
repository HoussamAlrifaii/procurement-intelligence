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
MARTS_SQL_DIR = SQL_DIR / "marts"
ANALYSIS_SQL_DIR = SQL_DIR / "analysis"
ML_SQL_DIR = SQL_DIR / "ml"
ASSISTANT_SQL_DIR = SQL_DIR / "assistant"

REFERENCE_DIR = PROJECT_ROOT / "reference"      # small lookup tables committed to the repository
CPV_DIVISIONS_PATH = REFERENCE_DIR / "cpv_divisions.csv"
COUNTRIES_PATH = REFERENCE_DIR / "countries.csv"
CPV_CODES_PATH = REFERENCE_DIR / "cpv_codes.csv"   # official CPV 2008 list, English names

MARTS_DIR = DATA_DIR / "marts"          # star-schema tables (Parquet) for Power BI
ANALYSIS_OUTPUT_DIR = DATA_DIR / "analysis"  # results of the sql/analysis queries (CSV)
ML_DATA_DIR = DATA_DIR / "ml"            # feature tables for the models (Parquet)
SINGLE_BID_FEATURES_PATH = ML_DATA_DIR / "single_bid_features.parquet"
PRICE_FEATURES_PATH = ML_DATA_DIR / "price_features.parquet"
MODELS_DIR = PROJECT_ROOT / "models"     # trained models, re-created by the training scripts

REPORTS_DIR = PROJECT_ROOT / "reports"
PROFILE_REPORT_PATH = REPORTS_DIR / "data_profile.md"
FIGURES_DIR = REPORTS_DIR / "figures"
SINGLE_BID_METRICS_PATH = REPORTS_DIR / "single_bid_metrics.json"
PRICE_METRICS_PATH = REPORTS_DIR / "price_metrics.json"

EVALUATION_DIR = PROJECT_ROOT / "evaluation"   # hand-written test cases for the assistant
ASSISTANT_CASES_PATH = EVALUATION_DIR / "assistant_cases.json"            # development set
ASSISTANT_HOLDOUT_CASES_PATH = EVALUATION_DIR / "assistant_cases_holdout.json"  # held-out set

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

# --- Machine learning -------------------------------------------------------

# Time-based split by publication year: train on the past, choose the model on
# the next year, and report the final result once on the most recent year.
TRAIN_END_YEAR = 2020     # 2019-2020 (plus the few December 2018 notices)
VALIDATION_YEAR = 2021
TEST_YEAR = 2022

# Buyer history only counts award notices published at least this many days
# earlier, so outcomes not yet public when the tender was advertised are excluded.
BUYER_HISTORY_LAG_DAYS = 180

# Pseudo-awards used to shrink a buyer's historical rate towards the overall rate.
BUYER_HISTORY_SMOOTHING = 20

# Fair price model: the 10th, 50th and 90th percentiles give an expected value
# with an 80% range. An award is flagged as unusual when it is more than
# PRICE_ANOMALY_FACTOR times above the 90th percentile or below the 10th.
PRICE_QUANTILES = [0.1, 0.5, 0.9]
PRICE_ANOMALY_FACTOR = 2.0

RANDOM_SEED = 42

# --- AI assistant -----------------------------------------------------------

# Market searches cover the two most recent years in the data.
ASSISTANT_FIRST_YEAR = 2021
ASSISTANT_LAST_YEAR = 2022

# Any provider with an OpenAI-compatible API works; Groq is the default.
# LLM_API_KEY, LLM_BASE_URL and LLM_MODEL can be set in .env.
DEFAULT_LLM_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"

# Upper limit on LLM <-> tool round trips for one question.
ASSISTANT_MAX_STEPS = 6

# --- Web app and API -----------------------------------------------------------

# The deployed app cannot run the pipeline, so it uses a small bundle: 2021-2022
# awards (only the columns the tools need), buyer names and the trained models.
# It is built by procurement.app_bundle and published as a GitHub Release asset.
APP_BUNDLE_DIR = DATA_DIR / "app"
APP_BUNDLE_NAME = "procurement_app_bundle"
APP_BUNDLE_URL = ("https://github.com/HoussamAlrifaii/procurement-intelligence/releases/download/"
                  "app-data-v1/procurement_app_bundle.zip")

# Questions one visitor may ask the AI assistant per session (protects the free LLM quota).
APP_MAX_QUESTIONS = 10

# --- Automation -----------------------------------------------------------------

# The monthly refresh writes its red-flag report here. It names public buyers, so,
# like the analysis results, it is kept out of the repository.
RED_FLAGS_DIR = DATA_DIR / "red_flags"
RED_FLAGS_REPORT_PATH = RED_FLAGS_DIR / "red_flags.md"
RED_FLAGS_SNAPSHOT_PATH = RED_FLAGS_DIR / "snapshot.json"   # compared with the next run
LOGS_DIR = PROJECT_ROOT / "logs"
RED_FLAGS_TOP = 20                    # rows per table in the report
BUYER_RATE_THRESHOLD = 0.8            # buyers single-bid in at least 80% of awards...
BUYER_GAP_THRESHOLD = 0.2             # ...or 20 points above their country
