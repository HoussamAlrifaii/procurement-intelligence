# Project plan

## 1. Problems addressed

1. **Weak competition wastes public money.** When a tender receives only one
   bid, there is no price pressure, and it can hide favouritism. Single-bid
   contracts are a widely used risk indicator in procurement research. They
   are **a signal to investigate, not proof of wrongdoing**.
2. **Patterns are hidden in millions of records.** Auditors and journalists
   cannot review every contract by hand.
3. **Small businesses lose out.** They lack the time and resources to monitor
   tender portals and study historical prices.

## 2. Users and use cases

| User | Scenario | Feature |
|---|---|---|
| **Small business owner** (e.g. a 20-person IT firm) | "We do network installation, €50k–500k. What fits us?" → market size, main buyers, past winners, typical winning price, level of competition | AI assistant (Phase 6) |
| **Auditor or journalist** | Map of single-bid rates → a region at 45% vs a 20% average → one vendor wins 70% of an agency's IT contracts → ranked red-flag list | SQL + Power BI (Phases 3–4) |
| **Procurement officer** | Enters a planned tender → "62% single-bid risk; main drivers: buyer history and sector" → adjusts the design; checks the budget against the expected price range | ML models (Phase 5) |

## 3. Data

| Source | Coverage | Role |
|---|---|---|
| TED (EU) contract award notices | 33 countries, 2019–2022: 4.3M award rows, 1.1M notices | Primary dataset; `number_offers` (the ML target) is filled for 67% of rows |
| World Bank contract awards | 130+ borrower countries, contracts signed 2019–2022: 143k rows | Global coverage; vendor and price analysis |

Expected field types: numeric (values, bid counts), categorical (country, CPV
sector code, procedure type), dates, free text (titles, descriptions) and
entities (buyer and vendor names). Phase 1 verified the fields against the
downloaded files; see [`reports/data_profile.md`](../reports/data_profile.md)
and the [Phase 1 documentation](phases/PHASE_1_DATA_PIPELINE.md).

Known challenges: inconsistent company names (entity resolution), missing
values, currency and outlier errors, and data volume (development starts on a
subset).

### Analytical model (star schema, Phase 3)

```
        dim_buyer        dim_vendor
             \              /
dim_category — fact_contract_award — dim_country
                    |
                 dim_date
```

ML target: `is_single_bid` = 1 if one offer, 0 if two or more (awarded contracts with a valid offer count; competitive procedures only, see Phase 2).

## 4. Roadmap

| Phase | Scope | Output |
|---|---|---|
| **0. Setup** ✅ | Repository, environment, CI | Reproducible project skeleton |
| **1. Data sourcing + pipeline** ✅ | Download, field verification, DuckDB load, quality checks | One-command data pipeline |
| **2. Cleaning + EDA** ✅ | Vendor-name standardisation, missing values, outliers | EDA notebook and cleaned tables |
| **3. SQL analysis** ✅ | Star schema; competition and concentration queries | SQL layer |
| **4. Power BI** ✅ | Four-page dashboard | Dashboard, DAX measures, screenshots, PDF |
| **5. Machine learning** ✅ | Single-bid risk classifier, fair price model with calibrated ranges and unusual-price flags, SHAP explanations | Evaluated models, model card |
| **6. AI assistant** ✅ | LLM assistant that searches markets by CPV code and calls both models as tools, with an evaluation set | Assistant + evaluation report |
| **7. API + app + deployment** ✅ | TenderLens Streamlit app, FastAPI, app data bundle, Dockerfile, CPV lookup | Web app + REST API |
| **8. Automation + polish** ✅ | Monthly refresh command, red-flag report, Windows schedule | Production-style workflow |

## 5. Automation

| Automation | Phase |
|---|---|
| One-command pipeline (download → clean → load → build tables) | 1–3 ✅ (raw, clean and star-schema layers) |
| Data quality checks that stop the pipeline on invalid data | 1 ✅ |
| Automated tests (`python -m pytest`) and a CI workflow definition (`.github/workflows/tests.yml`); Actions is currently disabled for this repository, so tests are run locally | 0 ✅ |
| Monthly refresh: one command from download to report and app bundle, scheduled with Windows Task Scheduler (`procurement/refresh.py`) | 8 ✅ |
| Red-flag report after each refresh: buyers to review, riskiest tenders, unusual prices, changes (`procurement/red_flags.py`) | 8 ✅ |

The Power BI report is refreshed from the processed data files in Power BI
Desktop. Scheduled refresh in the Power BI service requires an organisational
licence and is out of scope.

## 6. Technology

Python 3.12, pandas, DuckDB, rapidfuzz, Jupyter, matplotlib/seaborn,
scikit-learn, LightGBM (with built-in SHAP values), Power BI Desktop, Streamlit, FastAPI, LLM API, pytest,
GitHub Actions, Docker.
