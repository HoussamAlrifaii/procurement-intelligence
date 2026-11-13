"""Run the business-question queries in sql/analysis/ against the star schema.

Each query is a standalone .sql file that can also be run directly in DuckDB.
Results are saved as CSV in data/analysis/ (not committed: they name buyers and
vendors and are re-created from the data).

Usage (after the star schema exists):
    python -m procurement.analysis
"""
import duckdb

from procurement import config


def list_analyses():
    return sorted(path.stem for path in config.ANALYSIS_SQL_DIR.glob("*.sql"))


def run_analysis(connection, name):
    """Run sql/analysis/<name>.sql and return the result as a pandas DataFrame."""
    sql_text = (config.ANALYSIS_SQL_DIR / f"{name}.sql").read_text()
    return connection.sql(sql_text).df()


def main():
    config.ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        for name in list_analyses():
            result = run_analysis(connection, name)
            output_path = config.ANALYSIS_OUTPUT_DIR / f"{name}.csv"
            result.to_csv(output_path, index=False)
            print(f"  {name}: {len(result):,} rows -> {output_path.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
