"""Central project settings: every path in the project comes from here."""
from pathlib import Path

# 🎯 INTERVIEW FOCUS: why one config file?
# If paths were typed inside each script, moving a folder would break many files.
# Defining them once means every script agrees on where data lives.
# Building paths from this file's location (not the current working directory)
# makes the code work no matter which folder you run it from.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"              # downloaded files, never edited by hand
PROCESSED_DATA_DIR = DATA_DIR / "processed"  # cleaned outputs created by our code
DATABASE_PATH = DATA_DIR / "procurement.duckdb"

SQL_DIR = PROJECT_ROOT / "sql"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 📖 READ ONLY: folders the project needs before any phase can run.
REQUIRED_FOLDERS = [RAW_DATA_DIR, PROCESSED_DATA_DIR, SQL_DIR, REPORTS_DIR]

# 📖 READ ONLY: the Python version this project is written and tested for.
MINIMUM_PYTHON = (3, 12)
