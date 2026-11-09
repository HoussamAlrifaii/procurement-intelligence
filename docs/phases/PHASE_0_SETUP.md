# Phase 0: Project setup

**Goal:** a reproducible project skeleton, so that every later phase has a
defined place, runs identically on any machine, and is tested automatically.

## Contents

| File / folder | Purpose |
|---|---|
| `procurement/` | Python package containing all reusable project code |
| `procurement/config.py` | Single source of truth for paths and settings |
| `procurement/check_setup.py` | Environment verification (Python version, packages, folders, DuckDB) |
| `tests/` | Automated tests (pytest) |
| `.github/workflows/tests.yml` | CI: runs the environment check and tests on every push and pull request |
| `requirements.txt` | Pinned dependencies |
| `.gitignore` | Excludes data, secrets and local tooling files |
| `.env.example` | Template for secret settings (real values live in a git-ignored `.env`) |
| `data/raw`, `data/processed` | Source downloads and pipeline outputs (not committed) |
| `sql/`, `notebooks/`, `reports/` | SQL queries, exploratory analysis, generated reports |

## Design decisions

1. **Package plus notebooks, not notebooks alone.** Notebooks are used for
   exploration. Reusable logic lives in the `procurement` package, where it
   can be imported, tested and deployed.
2. **DuckDB as the analytical database.** It is an in-process SQL engine with a
   single-file database and no server to administer. It handles millions of
   rows on a laptop, and its SQL transfers to PostgreSQL, Snowflake or
   BigQuery. It can also query pandas DataFrames directly, which keeps Python
   preparation and SQL analysis in one workflow.
3. **Dependencies added per phase and pinned.** Each package enters
   `requirements.txt` in the phase that first needs it, with an exact version,
   so environments are reproducible and every dependency has a reason.
4. **Data is not version-controlled.** Source data is large and
   re-downloadable. The Phase 1 pipeline re-creates it with a single command.
5. **Paths resolved from the code location.** `config.PROJECT_ROOT` is derived
   from `__file__`, so paths are correct whether code runs from the project
   root, a notebook or CI.
6. **Checks fail loudly.** `check_setup` exits with a non-zero status on
   failure, so CI stops instead of continuing with a broken environment.

## Single-bid rate definition

The environment check runs the metric the project is built around:

```sql
AVG(CASE WHEN number_of_bids = 1 THEN 1.0 ELSE 0.0 END) AS single_bid_rate
```

Each contract is mapped to 1 (single bid) or 0 (competitive), and the mean of
that flag is the share of single-bid contracts in each group.

## Running locally

Requires Python 3.12 and Git.

```bash
git clone https://github.com/HoussamAlrifaii/procurement-intelligence
cd procurement-intelligence
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m procurement.check_setup
python -m pytest -q
```

On Windows, if PowerShell blocks the activation script, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

Expected output: every check reports `OK`, followed by `All checks passed`
and `3 passed`.

## Workflow

`main` always holds working code. Each phase is developed on its own branch
(`phase-N-name`) and merged through a pull request after CI passes.

## Next phase

Phase 1 downloads TED and World Bank contract award data for a defined subset
of countries and years, verifies field availability and completeness, and
loads the data into DuckDB with automated quality checks.
