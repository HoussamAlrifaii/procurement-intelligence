"""Check that this computer is ready for the project.

Run from the project folder:
    python -m procurement.check_setup

Prints one line per check and exits with an error code if anything failed,
so the same script works for a person and for automated CI.
"""
import importlib
import sys

from procurement import config

# 📖 READ ONLY: the import name of each package in requirements.txt.
# (Some import names differ from install names, e.g. python-dotenv -> dotenv.)
REQUIRED_PACKAGES = [
    "pandas",
    "numpy",
    "pyarrow",
    "duckdb",
    "requests",
    "rapidfuzz",
    "matplotlib",
    "seaborn",
    "dotenv",
    "pytest",
]


def check_python_version():
    """Return (passed, message) for the Python version."""
    # 📖 READ ONLY: sys.version_info is a tuple like (3, 12, 4, ...).
    current = sys.version_info[:2]
    passed = current >= config.MINIMUM_PYTHON
    message = f"Python {current[0]}.{current[1]} (need {config.MINIMUM_PYTHON[0]}.{config.MINIMUM_PYTHON[1]}+)"
    return passed, message


def check_packages():
    """Return a list of (passed, message), one per required package."""
    results = []
    for package_name in REQUIRED_PACKAGES:
        # 📖 READ ONLY: importlib imports a package from its name as a string.
        try:
            module = importlib.import_module(package_name)
            version = getattr(module, "__version__", "installed")
            results.append((True, f"{package_name} {version}"))
        except ImportError:
            results.append((False, f"{package_name} is missing: run pip install -r requirements.txt"))
    return results


def check_folders():
    """Create any missing project folders and return (passed, message)."""
    for folder in config.REQUIRED_FOLDERS:
        # 📖 READ ONLY: parents=True creates parent folders too;
        # exist_ok=True means "do nothing if it already exists".
        folder.mkdir(parents=True, exist_ok=True)
    return True, f"{len(config.REQUIRED_FOLDERS)} project folders ready"


def check_duckdb_sql():
    """Run a small SQL query on a pandas table and return (passed, message)."""
    import duckdb
    import pandas as pd

    # 🎯 INTERVIEW FOCUS: DuckDB can query a pandas DataFrame directly with SQL.
    # This is how the whole project works: Python loads and cleans data,
    # SQL answers the analytical questions. Here we test that it works with
    # three tiny made-up contracts (test values only, not real data).
    contracts = pd.DataFrame({
        "country": ["DE", "DE", "FR"],
        "number_of_bids": [1, 4, 1],
    })

    query = """
        SELECT
            country,
            COUNT(*) AS contracts,
            AVG(CASE WHEN number_of_bids = 1 THEN 1.0 ELSE 0.0 END) AS single_bid_rate
        FROM contracts
        GROUP BY country
        ORDER BY country
    """
    # 🎯 INTERVIEW FOCUS: the CASE WHEN ... AVG pattern above turns a yes/no
    # condition into a rate. It is the core of the "single-bid rate" metric
    # we will use in SQL and Power BI later.

    # 📖 READ ONLY: duckdb.sql() finds the `contracts` DataFrame by its
    # Python variable name; .df() returns the result as a DataFrame.
    result = duckdb.sql(query).df()

    expected_rates = [0.5, 1.0]  # DE: 1 of 2 contracts single-bid; FR: 1 of 1
    passed = result["single_bid_rate"].tolist() == expected_rates
    return passed, "DuckDB SQL query on a pandas table"


def run_all_checks():
    """Run every check and return a list of (passed, message)."""
    results = [check_python_version()]
    results.extend(check_packages())
    results.append(check_folders())
    results.append(check_duckdb_sql())
    return results


def main():
    # 📖 READ ONLY: print a readable report, then exit with code 1 on failure
    # (a non-zero exit code is how CI knows a step failed).
    results = run_all_checks()
    for passed, message in results:
        symbol = "OK  " if passed else "FAIL"
        print(f"[{symbol}] {message}")

    failures = [message for passed, message in results if not passed]
    if failures:
        print(f"\n{len(failures)} check(s) failed. Fix them before Phase 1.")
        sys.exit(1)
    print("\nAll checks passed. Your environment is ready for Phase 1.")


if __name__ == "__main__":
    main()
