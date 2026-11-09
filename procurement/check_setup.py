"""Verify that the local environment is ready to run the project.

Usage (from the project root):
    python -m procurement.check_setup

Prints one line per check and exits with a non-zero code if any check fails,
so the same script serves both local setup and CI.
"""
import importlib
import sys

from procurement import config

# Import names of the packages in requirements.txt
# (python-dotenv is imported as `dotenv`).
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
    """Return (passed, message) for the running Python version."""
    current = sys.version_info[:2]
    passed = current >= config.MINIMUM_PYTHON
    required = f"{config.MINIMUM_PYTHON[0]}.{config.MINIMUM_PYTHON[1]}"
    message = f"Python {current[0]}.{current[1]} (requires {required}+)"
    return passed, message


def check_packages():
    """Return a list of (passed, message), one entry per required package."""
    results = []
    for package_name in REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(package_name)
            version = getattr(module, "__version__", "installed")
            results.append((True, f"{package_name} {version}"))
        except ImportError:
            results.append((False, f"{package_name} missing: run pip install -r requirements.txt"))
    return results


def check_folders():
    """Create any missing project folders and return (passed, message)."""
    for folder in config.REQUIRED_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
    return True, f"{len(config.REQUIRED_FOLDERS)} project folders ready"


def check_duckdb_sql():
    """Run a single-bid-rate query on a small in-memory table.

    Confirms that DuckDB can query a pandas DataFrame directly, which is how the
    pipeline combines Python data preparation with SQL analysis. The three rows
    are synthetic test values, not procurement records.
    """
    import duckdb
    import pandas as pd

    contracts = pd.DataFrame({
        "country": ["DE", "DE", "FR"],
        "number_of_bids": [1, 4, 1],
    })

    # Averaging a 1/0 flag gives the share of rows where the condition holds.
    # This is the same definition of single-bid rate used in later analysis.
    query = """
        SELECT
            country,
            COUNT(*) AS contracts,
            AVG(CASE WHEN number_of_bids = 1 THEN 1.0 ELSE 0.0 END) AS single_bid_rate
        FROM contracts
        GROUP BY country
        ORDER BY country
    """
    # DuckDB resolves `contracts` to the DataFrame variable in local scope.
    result = duckdb.sql(query).df()

    expected_rates = [0.5, 1.0]  # DE: 1 of 2 single-bid; FR: 1 of 1
    passed = result["single_bid_rate"].tolist() == expected_rates
    return passed, "DuckDB SQL query on a pandas DataFrame"


def run_all_checks():
    """Run every check and return a list of (passed, message)."""
    results = [check_python_version()]
    results.extend(check_packages())
    results.append(check_folders())
    results.append(check_duckdb_sql())
    return results


def main():
    results = run_all_checks()
    for passed, message in results:
        status = "OK  " if passed else "FAIL"
        print(f"[{status}] {message}")

    failures = [message for passed, message in results if not passed]
    if failures:
        print(f"\n{len(failures)} check(s) failed.")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
