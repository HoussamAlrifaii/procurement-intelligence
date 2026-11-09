# Procurement Intelligence

**Turning public procurement data into better competition, faster auditing and
fairer access for small businesses.**

Governments publish every contract they award: who bought what, from whom, at
what price, and how many companies competed. This project turns that raw data
into answers:

| Problem | Solution | User |
|---|---|---|
| Tenders with only one bidder have no price competition | ML model predicting single-bid risk **before** publication, with explanations | Procurement officers |
| Suspicious patterns are hidden in millions of records | SQL analysis + Power BI dashboard of competition, vendor concentration and unusual prices | Auditors, journalists |
| Small businesses can't find or price opportunities | AI assistant matching a company to relevant tenders, past winners and prices | Small and medium businesses |

> 🚧 **Status: in development.** Phases 0–1 complete: project setup and a
> reproducible raw data pipeline. See the [project plan](docs/PROJECT_PLAN.md).

## Tech stack

Python · pandas · DuckDB (SQL) · scikit-learn · Power BI · LLM API ·
FastAPI · Streamlit · Docker · GitHub Actions

## Quick start (Python 3.12)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m procurement.check_setup
python -m pytest -q
python -m procurement.pipeline    # download and load 2019-2022 (~490 MB download)
```

The pipeline writes a DuckDB database to `data/procurement.duckdb` and a data
profile to [`reports/data_profile.md`](reports/data_profile.md). Details:
[Phase 1 documentation](docs/phases/PHASE_1_DATA_PIPELINE.md).

## Project structure

```
procurement/   Python package (pipeline, models, app code)
sql/           SQL queries, kept as .sql files
notebooks/     Exploratory analysis
data/          Downloaded and processed data (not committed; re-created by code)
reports/       Generated reports and figures
docs/          Project plan and one explanation file per phase
tests/         Automated tests
```

## Data sources

- [TED (Tenders Electronic Daily) CSV subset](https://data.europa.eu/data/datasets/ted-csv):
  EU contract award notices, 2019–2022.
- [World Bank: Contract Awards in Investment Project Financing](https://financesone.worldbank.org/x/DS00005):
  contracts in World Bank-financed projects, signed 2019–2022.

Both are published as open data by their respective institutions. Each data
source's own terms of use apply.
