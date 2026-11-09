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

> 🚧 **Status: in development.** Phase 0 (project setup) is complete.
> See the [project plan](docs/PROJECT_PLAN.md) for the roadmap.

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
```

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

- [TED: Tenders Electronic Daily](https://ted.europa.eu): EU contract award notices.
- [World Bank contract awards](https://finances.worldbank.org): global coverage.

Exact fields, coverage and licence terms are verified in Phase 1 and documented there.
