"""Build the clean layer: typed, de-duplicated, labelled tables.

All cleaning rules live in sql/clean/*.sql, each numbered and explained there.
This module only runs those files in order and reports row counts.

Usage (after the pipeline has built the raw layer):
    python -m procurement.clean
"""
import duckdb

from procurement import config
from procurement.load import count_rows
from procurement.sql_runner import run_sql_file, sql_string


def register_macros(connection):
    """Create the shared SQL helper functions (standardize_name, yes_no)."""
    run_sql_file(connection, config.CLEAN_SQL_DIR / "macros.sql")


def clean_ted(connection, output_path=None):
    output_path = output_path or config.TED_CLEAN_PATH
    run_sql_file(
        connection,
        config.CLEAN_SQL_DIR / "clean_ted_awards.sql",
        raw_table=config.TED_TABLE,
        clean_view=config.TED_CLEAN_VIEW,
        output_path=sql_string(output_path),
        cpv_reference_path=sql_string(config.CPV_DIVISIONS_PATH),
    )
    return count_rows(connection, config.TED_CLEAN_VIEW)


def clean_world_bank(connection, output_path=None):
    output_path = output_path or config.WORLD_BANK_CLEAN_PATH
    run_sql_file(
        connection,
        config.CLEAN_SQL_DIR / "clean_world_bank_awards.sql",
        raw_table=config.WORLD_BANK_TABLE,
        clean_view=config.WORLD_BANK_CLEAN_VIEW,
        output_path=sql_string(output_path),
    )
    return count_rows(connection, config.WORLD_BANK_CLEAN_VIEW)


def build_clean_layer(connection):
    register_macros(connection)
    ted_rows = clean_ted(connection)
    world_bank_rows = clean_world_bank(connection)
    print(f"  {config.TED_CLEAN_VIEW}: {ted_rows:,} rows (one per contract award)")
    print(f"  {config.WORLD_BANK_CLEAN_VIEW}: {world_bank_rows:,} rows (one per supplier on a contract)")


def main():
    with duckdb.connect(str(config.DATABASE_PATH)) as connection:
        build_clean_layer(connection)


if __name__ == "__main__":
    main()
