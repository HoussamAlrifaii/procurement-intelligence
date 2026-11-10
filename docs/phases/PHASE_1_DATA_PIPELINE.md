# Phase 1: Data sourcing and raw data pipeline

**Goal:** one reproducible command that downloads the source data, records
exactly which files were used, stores them efficiently, loads them into DuckDB,
and stops if the data cannot be trusted.

```bash
python -m procurement.pipeline                     # 2019-2022 (default)
python -m procurement.pipeline --years 2021 2022   # smaller, faster run
python -m procurement.pipeline --skip-download     # reuse files in data/raw
```

## 1. Sources (verified against the downloaded files)

| Source | Download | Format | Notes |
|---|---|---|---|
| **TED contract award notices** (EU open data portal, dataset `ted-csv`) | `https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-{year}.zip` | One zip per publication year containing one CSV (comma-separated, quoted, UTF-8) | ~100 MB zipped, ~700 MB unzipped per year. Columns documented in the official *TED CSV Open Data – Notes and Codebook*. |
| **World Bank: Contract Awards in Investment Project Financing (since FY 2020)** | `https://financesonefiles.worldbank.org/f-one/DS00005/RS00005/Contract_Awards_in_Investment_Project_Financing__Since_FY_2020_.csv` | One CSV | A live file updated by the World Bank. The manifest records the download time and fingerprint of the copy used. |

**Why 2019–2022:** recent years in the stable TED CSV format. From 2023 the EU
moved to eForms notices, which changes how award data is structured; mixing
formats would add a data-consistency problem before any analysis starts.

**Grain:** a TED row is one *award* within a notice. One notice can contain
several lots and several awards, so row counts and notice counts differ.

## 2. Pipeline design

```
download            convert                 load                  verify
data/raw/  ──────▶  data/processed/  ────▶  DuckDB raw views  ──▶ quality rules + profile
*.zip, *.csv        *.parquet (per file)    raw_ted_awards        sql/quality/*.sql
manifest.json                               raw_world_bank_awards reports/data_profile.md
```

| Module | Responsibility |
|---|---|
| `procurement/download.py` | Streams each file in 1 MB chunks to a `.part` file, renames it only when complete, skips files already present, records URL, size, SHA-256 and download time in `data/raw/manifest.json` |
| `procurement/load.py` | Extracts each TED CSV to a temporary folder, converts it to Parquet, deletes the CSV, then creates DuckDB views over the Parquet files |
| `procurement/quality.py` + `sql/quality/` | Runs each SQL rule and reports failing row counts by severity |
| `procurement/profile.py` + `sql/profile/` | Writes `reports/data_profile.md`: fill rate and variety of every column |
| `procurement/pipeline.py` | Orchestrates the steps; exits with code 1 on a critical failure |
| `procurement/sql_runner.py` | Reads `.sql` files and fills their placeholders |

## 3. Design decisions

1. **Raw layer stores everything as text.** Values are kept exactly as
   published (`all_varchar`). Dates such as `29/12/21`, empty strings and
   codes are not interpreted yet. Converting types silently at load time would
   hide decisions (and errors) inside the loader; Phase 2 makes each one
   explicit.
2. **Parquet as the storage format, DuckDB views on top.** Parquet is
   columnar and compressed, so it is much smaller than CSV and fast to query.
   One file per year makes the pipeline incremental: a year already converted
   is skipped. The raw "tables" are views that read the Parquet files directly,
   so the data is stored once. Views use absolute paths; if the project folder
   moves, re-run the pipeline with `--skip-download` to recreate them.
3. **`union_by_name` when combining years.** Columns are matched by name, so a
   column that exists only in some years becomes `NULL` elsewhere instead of
   shifting data into the wrong column.
4. **Column names normalised once.** `ID_NOTICE_CAN` → `id_notice_can`,
   `Supplier Contract Amount (USD)` → `supplier_contract_amount_usd`. TED's
   `YEAR` is renamed to `notice_year` because `year` is a reserved SQL word.
5. **Lineage.** Each row carries `source_file`; each file has a SHA-256 in the
   manifest. Any number in later phases can be traced to the exact input.
6. **Atomic, idempotent downloads.** Re-running never re-downloads complete
   files, and an interrupted download cannot be mistaken for a complete one.
7. **Quality rules as SQL files with severities.**

   | Severity | Meaning | Example |
   |---|---|---|
   | critical | Data cannot be trusted; the pipeline exits with code 1 | missing notice IDs, years outside the requested range, empty tables |
   | warning | Reported for investigation in the cleaning phase | non-numeric or negative values |
   | info | Context only | rows without a number of offers, cancelled notices |

   A rule that fails to run (e.g. a missing column) counts as failed, so a
   schema change in the source cannot pass silently.
8. **World Bank rows filtered to the analysis years** (by contract signing
   year) so both sources cover the same period.

## 4. Results of the pipeline run

Full run on 2019–2022 (downloaded 9 November 2026). Download about 490 MB;
conversion and loading about 40 seconds after download. Raw Parquet files total
about 330 MB. The DuckDB database itself is under 1 MB, because raw tables are
views over the Parquet files (an earlier version that copied the data into
DuckDB tables produced a 1.8 GB database for the same content).

**TED (`raw_ted_awards`)**: 4,295,572 award rows, 1,118,490 notices, 76 columns, 33 countries.

| Year | Award rows | Notices | `number_offers` filled | Single-offer share (rows with a value) |
|---|---:|---:|---:|---:|
| 2019 | 990,811 | 264,771 | 68.0% | 32.0% |
| 2020 | 1,070,272 | 267,596 | 64.6% | 32.5% |
| 2021 | 1,162,663 | 285,506 | 65.3% | 30.9% |
| 2022 | 1,071,826 | 300,617 | 69.9% | 32.5% |

**World Bank (`raw_world_bank_awards`)**: 142,870 contracts signed 2019–2022
(16,250 / 42,165 / 42,412 / 42,043 per year), 130–138 borrower countries per
year. 2019 is partial: the source starts at fiscal year 2020, which begins in
July 2019.

**Quality rules:** all critical and warning rules passed. Info: 1,421,561 TED
rows (33.1%) have no number of offers and cannot be used as model labels;
4 rows belong to cancelled notices.

**What this means for the project**

- The single-bid target is viable: 2,874,011 labelled award rows, about 32%
  single-offer. These are raw row-level shares before cleaning and
  de-duplication, not final statistics.
- Award-level fields (`number_offers`, `award_value_euro`, `win_name`,
  `dt_award`) are filled for roughly two thirds of rows. Phase 2 investigates
  why (for example lots that were not awarded) before deciding how to treat them.
- Full column-by-column details: [`reports/data_profile.md`](../../reports/data_profile.md).

## 5. Tests

`tests/test_pipeline.py` runs the load, quality and profile steps on small
synthetic fixtures (`tests/fixtures/`) that mimic the real file structure, so
CI never downloads data. Covered: download skipping, fingerprints, SQL quoting,
raw-layer typing and lineage, year filtering, rule severities, a rule that
cannot run, and the profile report.

## 6. Next phase

Phase 2 (cleaning and EDA) turns the raw text tables into typed, cleaned
tables: date parsing, numeric conversion, award and notice granularity,
missing-value handling, outliers, and vendor-name standardisation.
