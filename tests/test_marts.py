"""Tests for the star schema (sql/marts/) and the analysis queries (sql/analysis/)."""
import zipfile
from pathlib import Path

import duckdb
import pytest

from procurement.analysis import list_analyses, run_analysis
from procurement.clean import clean_ted, clean_world_bank, register_macros
from procurement.load import load_ted, load_world_bank
from procurement.marts import build_marts

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def connection(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("marts")
    zip_path = tmp_path / "ted-contract-award-notices-2022.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(FIXTURES / "ted_clean_sample.csv", arcname="export_CAN_2022.csv")

    with duckdb.connect() as in_memory_connection:
        load_ted(in_memory_connection, [zip_path], tmp_path)
        load_world_bank(in_memory_connection, FIXTURES / "world_bank_clean_sample.csv", tmp_path, [2022])
        register_macros(in_memory_connection)
        clean_ted(in_memory_connection, output_path=tmp_path / "ted_clean.parquet")
        clean_world_bank(in_memory_connection, output_path=tmp_path / "wb_clean.parquet")
        build_marts(in_memory_connection, output_dir=tmp_path / "marts")
        yield in_memory_connection


def scalar(connection, sql):
    return connection.sql(sql).fetchone()[0]


def test_fact_award_keeps_every_clean_award(connection):
    assert scalar(connection, "SELECT COUNT(*) FROM fact_award") == scalar(connection, "SELECT COUNT(*) FROM ted_awards")


def test_dimension_keys_are_unique(connection):
    for table, key in [("dim_buyer", "buyer_key"), ("dim_vendor", "vendor_key"),
                       ("dim_sector", "sector_key"), ("dim_procedure", "procedure_key"), ("dim_date", "date_key")]:
        duplicates = scalar(connection, f"SELECT COUNT(*) - COUNT(DISTINCT {key}) FROM {table}")
        assert duplicates == 0, table


def test_every_fact_key_exists_in_its_dimension(connection):
    checks = {
        "buyer": "SELECT COUNT(*) FROM fact_award f LEFT JOIN dim_buyer d USING (buyer_key) WHERE d.buyer_key IS NULL",
        "sector": "SELECT COUNT(*) FROM fact_award f LEFT JOIN dim_sector d USING (sector_key) WHERE d.sector_key IS NULL",
        "procedure": "SELECT COUNT(*) FROM fact_award f LEFT JOIN dim_procedure d USING (procedure_key) WHERE d.procedure_key IS NULL",
        "date": "SELECT COUNT(*) FROM fact_award f LEFT JOIN dim_date d USING (date_key) WHERE d.date_key IS NULL",
    }
    for name, sql in checks.items():
        assert scalar(connection, sql) == 0, name


def test_vendor_key_is_missing_only_without_a_winner(connection):
    orphans = scalar(connection, """
        SELECT COUNT(*) FROM fact_award f JOIN ted_awards a USING (award_id)
        WHERE f.vendor_key IS NULL AND a.winner_name_std IS NOT NULL
    """)
    assert orphans == 0


def test_vendor_shared_by_both_facts(connection):
    # 'Example Builder Sp. z o.o.' (PL) wins in the TED fixture and supplies a World Bank contract.
    row = connection.sql("""
        SELECT in_ted, in_world_bank FROM dim_vendor
        WHERE vendor_name_std = 'example builder' AND vendor_country = 'PL'
    """).fetchone()
    assert row == (True, True)


def test_plausible_value_measure(connection):
    values = dict(connection.sql("SELECT award_id, award_value_eur_plausible FROM fact_award").fetchall())
    assert values[101] == 50000      # plausible value kept
    assert values[102] is None       # too low -> excluded from value sums
    assert values[104] is None       # too high -> excluded from value sums


def test_every_analysis_query_runs(connection):
    for name in list_analyses():
        result = run_analysis(connection, name)
        assert result is not None, name
