"""Build the star schema (data marts) used by the SQL analysis and Power BI.

Each table is built by one file in sql/marts/, in numbered order: dimensions
first, then the fact tables that look up their keys. Every table is written to
data/marts/<table>.parquet and exposed as a DuckDB view of the same name.

Usage (after the clean layer exists):
    python -m procurement.marts
"""
import duckdb

from procurement import config
from procurement.clean import register_macros
from procurement.load import count_rows
from procurement.sql_runner import run_sql_file, sql_string


def table_name(sql_path):
    """'06_fact_award.sql' -> 'fact_award'."""
    return sql_path.stem.split("_", 1)[1]


def build_marts(connection, output_dir=None):
    output_dir = output_dir or config.MARTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    register_macros(connection)

    row_counts = {}
    for sql_path in sorted(config.MARTS_SQL_DIR.glob("*.sql")):
        name = table_name(sql_path)
        run_sql_file(
            connection,
            sql_path,
            output_path=sql_string(output_dir / f"{name}.parquet"),
            cpv_reference_path=sql_string(config.CPV_DIVISIONS_PATH),
            countries_path=sql_string(config.COUNTRIES_PATH),
        )
        row_counts[name] = count_rows(connection, name)
        print(f"  {name}: {row_counts[name]:,} rows")
    return row_counts


def main():
    with duckdb.connect(str(config.DATABASE_PATH)) as connection:
        build_marts(connection)


if __name__ == "__main__":
    main()
