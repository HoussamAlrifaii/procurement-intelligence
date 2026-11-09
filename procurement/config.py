"""Central project settings. Every path used in the project is defined here."""
from pathlib import Path

# Paths are built from this file's location rather than the current working
# directory, so scripts, notebooks and CI resolve the same locations no matter
# where they are launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"              # downloaded source files, never edited by hand
PROCESSED_DATA_DIR = DATA_DIR / "processed"  # cleaned outputs produced by the pipeline
DATABASE_PATH = DATA_DIR / "procurement.duckdb"

SQL_DIR = PROJECT_ROOT / "sql"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Folders that must exist before the pipeline runs.
REQUIRED_FOLDERS = [RAW_DATA_DIR, PROCESSED_DATA_DIR, SQL_DIR, REPORTS_DIR]

# Python version the project is developed and tested against.
MINIMUM_PYTHON = (3, 12)
