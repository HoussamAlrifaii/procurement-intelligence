"""Tests for the cleaning rules in sql/clean/, using synthetic fixtures."""
import zipfile
from pathlib import Path

import duckdb
import pytest

from procurement import config
from procurement.clean import clean_ted, clean_world_bank, register_macros
from procurement.load import load_ted, load_world_bank

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def connection(tmp_path):
    zip_path = tmp_path / "ted-contract-award-notices-2022.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(FIXTURES / "ted_clean_sample.csv", arcname="export_CAN_2022.csv")

    with duckdb.connect() as in_memory_connection:
        load_ted(in_memory_connection, [zip_path], tmp_path)
        load_world_bank(in_memory_connection, FIXTURES / "world_bank_clean_sample.csv", tmp_path, [2022])
        register_macros(in_memory_connection)
        clean_ted(in_memory_connection, output_path=tmp_path / "ted_clean.parquet")
        clean_world_bank(in_memory_connection, output_path=tmp_path / "wb_clean.parquet")
        yield in_memory_connection


def ted_award(connection, award_id):
    relation = connection.sql(f"SELECT * FROM {config.TED_CLEAN_VIEW} WHERE award_id = {award_id}")
    rows = relation.fetchall()
    if not rows:
        return None
    return dict(zip(relation.columns, rows[0]))


def test_one_row_per_award_without_cancelled_or_lot_only_rows(connection):
    award_ids = connection.sql(f"SELECT award_id FROM {config.TED_CLEAN_VIEW} ORDER BY 1").fetchall()
    # 101 appears twice in the raw data (two lots) -> once; 105 is cancelled;
    # the row without an award ID is a lot description only.
    assert [row[0] for row in award_ids] == [101, 102, 103, 104, 106]


def test_single_bid_label(connection):
    assert ted_award(connection, 101)["is_single_bid"] == 1   # 1 offer
    assert ted_award(connection, 102)["is_single_bid"] == 0   # 4 offers
    assert ted_award(connection, 103)["is_single_bid"] is None  # not awarded
    assert ted_award(connection, 104)["is_single_bid"] is None  # 999 placeholder
    assert ted_award(connection, 106)["is_single_bid"] is None  # 0 offers


def test_award_status_and_value_flags(connection):
    assert ted_award(connection, 103)["award_status"] == "not_awarded_unsuccessful"
    assert ted_award(connection, 101)["award_value_quality"] == "plausible"
    assert ted_award(connection, 102)["award_value_quality"] == "too_low"
    assert ted_award(connection, 104)["award_value_quality"] == "too_high"
    assert ted_award(connection, 103)["award_value_quality"] == "missing"


def test_types_and_labels(connection):
    award = ted_award(connection, 101)
    assert str(award["publication_date"]) == "2022-02-14"
    assert award["contract_type"] == "Supplies"
    assert award["procedure_type"] == "Open"
    assert award["is_competitive_procedure"] is True
    assert award["cpv_division_name"] == "Software package and information systems"
    assert award["is_eu_funded"] is True
    assert ted_award(connection, 103)["is_competitive_procedure"] is False  # NOC


def test_multiple_winners_keep_first_and_count(connection):
    award = ted_award(connection, 102)
    assert award["winner_name"] == "EXAMPLE SOFTWARE, S.A."
    assert award["winner_name_std"] == "example software"
    assert award["winner_count"] == 2
    assert award["winner_country"] == "ES"
    assert award["winner_is_sme"] is False


def test_standardized_names_match_across_spellings(connection):
    names = connection.sql(
        "SELECT standardize_name('Example Software GmbH'), standardize_name('EXAMPLE SOFTWARE, S.A.')"
    ).fetchone()
    assert names == ("example software", "example software")


def test_world_bank_joint_venture_amount_counted_once(connection):
    totals = dict(connection.sql(
        f"SELECT contract_id, SUM(amount_usd_for_totals) FROM {config.WORLD_BANK_CLEAN_VIEW} GROUP BY 1"
    ).fetchall())
    assert totals["9001"] == 1000   # same amount on both partner rows -> counted once
    assert totals["9002"] == 1000   # different shares 300 + 700 -> both kept
    assert totals["9003"] == 50


def test_world_bank_types_and_flags(connection):
    row = connection.sql(
        f"SELECT signing_date, amount_quality, supplier_name_std FROM {config.WORLD_BANK_CLEAN_VIEW} "
        "WHERE contract_id = '9003'"
    ).fetchone()
    assert str(row[0]) == "2022-05-02"
    assert row[1] == "too_low"
    assert row[2] == "example consultant"
