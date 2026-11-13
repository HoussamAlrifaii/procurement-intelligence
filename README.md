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

> 🚧 **Status: in development.** Phases 0–3 complete: project setup, a
> reproducible data pipeline, cleaning and exploratory analysis, star schema
> and SQL analysis.
> See the [project plan](docs/PROJECT_PLAN.md).

## Highlights so far

From 3.56 million EU contract awards (2019–2022) and 143k World Bank contracts
([full analysis](notebooks/02_eda.ipynb)):

- **32% of awarded EU contracts received a single offer**, ranging from 60% in Slovenia to 6% in Iceland.
- Procedures without a call for competition are single-bid **86%** of the time; competitive procedures **31%**.
- Single bidding falls with contract size: **38%** under EUR 10k, **14%** above EUR 10M.
- **672 companies** won both EU tenders and World Bank contracts.
- Single bidding rose in **22 of 33** countries between 2019 and 2022 ([SQL analysis](notebooks/03_sql_analysis.ipynb)).
- **13.1%** of large buyers have highly concentrated spending (HHI ≥ 2,500).
- Correcting repeated joint-venture amounts removes **USD 4.4 bn** of double counting from World Bank totals.

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

The pipeline writes a DuckDB database to `data/procurement.duckdb`, a data
profile to [`reports/data_profile.md`](reports/data_profile.md), the clean
tables `ted_awards` and `world_bank_awards`, and a star schema (two fact tables,
five dimensions) in `data/marts/` for analysis and Power BI. Details:
[Phase 1](docs/phases/PHASE_1_DATA_PIPELINE.md) ·
[Phase 2](docs/phases/PHASE_2_CLEANING_EDA.md) ·
[Phase 3](docs/phases/PHASE_3_SQL_ANALYSIS.md).

## Project structure

```
procurement/   Python package (pipeline, models, app code)
sql/           SQL queries, kept as .sql files
notebooks/     Exploratory analysis
reference/     Small lookup tables (e.g. CPV sector names)
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
