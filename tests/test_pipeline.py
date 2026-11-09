"""Tests for download, load, quality and profile steps, using synthetic fixtures."""
import zipfile
from pathlib import Path

import duckdb
import pytest

from procurement import config, download
from procurement.load import load_ted, load_world_bank
from procurement.profile import write_profile_report
from procurement.quality import run_quality_checks
from procurement.sql_runner import sql_string

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def connection():
    with duckdb.connect() as in_memory_connection:
        yield in_memory_connection


@pytest.fixture
def ted_zip(tmp_path):
    """Zip the TED fixture the same way the real yearly files are packaged."""
    zip_path = tmp_path / "ted-contract-award-notices-2022.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(FIXTURES / "ted_sample.csv", arcname="export_CAN_2022.csv")
    return zip_path


@pytest.fixture
def loaded(connection, ted_zip, tmp_path):
    load_ted(connection, [ted_zip], tmp_path)
    load_world_bank(connection, FIXTURES / "world_bank_sample.csv", tmp_path, [2021, 2022])
    return connection


def test_ted_url_uses_the_year():
    assert download.ted_url(2020).endswith("ted-contract-award-notices-2020.zip")


def test_download_skips_existing_file(tmp_path, monkeypatch):
    existing = tmp_path / "already_here.zip"
    existing.write_bytes(b"data")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("no network call expected for an existing file")

    monkeypatch.setattr(download.requests, "get", fail_if_called)
    assert download.download_file("https://example.invalid/file.zip", existing) is False


def test_sha256_fingerprint(tmp_path):
    sample = tmp_path / "sample.txt"
    sample.write_bytes(b"abc")
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert download.sha256_of_file(sample) == expected


def test_sql_string_escapes_quotes():
    assert sql_string("O'Brien") == "'O''Brien'"


def test_ted_load_keeps_all_rows_as_text_with_clean_names(loaded):
    columns = {row[0]: row[1] for row in loaded.sql(f"DESCRIBE {config.TED_TABLE}").fetchall()}
    assert "id_notice_can" in columns
    assert "notice_year" in columns            # YEAR renamed explicitly
    assert "source_file" in columns            # lineage column added
    assert set(columns.values()) == {"VARCHAR"}  # raw layer: no type conversion
    row_count = loaded.sql(f"SELECT COUNT(*) FROM {config.TED_TABLE}").fetchone()[0]
    assert row_count == 4                      # no rows dropped or cleaned


def test_world_bank_load_filters_to_requested_years(loaded):
    years = loaded.sql(
        f"SELECT DISTINCT contract_signed_calendar_year FROM {config.WORLD_BANK_TABLE} ORDER BY 1"
    ).fetchall()
    assert years == [("2021",), ("2022",)]


def test_quality_rules_on_fixture(loaded):
    results = {result.name: result for result in run_quality_checks(loaded, years=[2021, 2022])}
    assert results["ted_notice_id_present"].passed
    assert results["ted_number_offers_missing"].failing_rows == 1
    assert results["ted_cancelled_notices"].failing_rows == 1
    assert not any(result.blocks_pipeline for result in results.values())


def test_year_outside_scope_blocks_pipeline(loaded):
    results = {result.name: result for result in run_quality_checks(loaded, years=[2022])}
    year_rule = results["ted_notice_year_in_scope"]
    assert year_rule.failing_rows == 1        # the 2021 row is out of scope
    assert year_rule.blocks_pipeline


def test_rule_that_cannot_run_counts_as_failure(connection):
    results = {result.name: result for result in run_quality_checks(connection, years=[2022])}
    assert results["ted_table_has_rows"].error   # table does not exist
    assert results["ted_table_has_rows"].blocks_pipeline


def test_profile_report_is_written(loaded, tmp_path):
    report = write_profile_report(loaded, [config.TED_TABLE, config.WORLD_BANK_TABLE],
                                  output_path=tmp_path / "profile.md")
    text = report.read_text()
    assert "`raw_ted_awards`" in text
    assert "| `number_offers` | 75.0% |" in text
