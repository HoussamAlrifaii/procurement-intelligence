# Project plan

## 1. The problems

1. **Weak competition wastes public money.** When a tender gets only one bid,
   there is no price pressure, and it can hide favouritism. Single-bid
   contracts are a widely used risk indicator in procurement research. They
   are **a signal to investigate, not proof of wrongdoing**.
2. **Patterns are hidden in millions of records.** Auditors and journalists
   cannot review every contract by hand.
3. **Small businesses lose out.** They lack the time and teams to search tender
   portals and study past prices.

## 2. Users and how they use it

| User | Example | Feature |
|---|---|---|
| **Sara**, owner of a 20-person IT company | "We do network installation, €50k–500k. What fits us?" → matching tenders, past winners, typical winning price | AI assistant (Phase 6) |
| **Omar**, auditor or journalist | Map of single-bid rates → region at 45% vs 20% average → one vendor wins 70% of an agency's IT contracts → ranked red-flag list | SQL + Power BI (Phases 3–4) |
| **Lina**, procurement officer | Enters planned tender → "62% single-bid risk; main driver: 15-day window vs 35 typical" → extends window | ML model (Phase 5) |

## 3. Data

| Source | Coverage | Role |
|---|---|---|
| TED (EU) contract award notices | EU/EEA, many years | Main dataset; expected to record the number of bids received (the ML target) |
| World Bank contract awards | Developing countries, global | Global coverage, vendor and price analysis |

Expected field types: numbers (values, bid counts), categories (country, CPV
sector code, procedure type), dates, free text (titles, descriptions) and
entities (buyer and vendor names). **Phase 1 verifies which fields actually
exist and how complete they are before anything is built on them.**

Known challenges: inconsistent company names (entity resolution), missing
values, currency and outlier errors, and data size (start with a subset).

### SQL model (star schema, Phase 3)

```
        dim_buyer        dim_vendor
             \              /
dim_category — fact_contract_award — dim_country
                    |
                 dim_date
```

ML target: `single_bid = 1 if number_of_bids == 1 else 0`.

## 4. Phases

| Week | Phase | Output | Main skill |
|---|---|---|---|
| 0 | **0. Setup** ✅ | Repo, environment, rules, CI | Tools |
| 1–2 | **1. Data sourcing + pipeline** | Download, verify fields, load into DuckDB, quality checks | Data engineering |
| 2–3 | **2. Cleaning + EDA** | Vendor-name matching, missing values, EDA notebook | EDA |
| 3–4 | **3. SQL analysis** | Star schema; competition and concentration queries | SQL |
| 4–5 | **4. Power BI** | Four-page dashboard | Power BI / DAX |
| 5–7 | **5. ML** | Single-bid risk classifier + price anomaly detection, SHAP explanations | ML |
| 7–8 | **6. AI assistant** | Tender search + Claude assistant that calls the model as a tool, with an evaluation set | AI engineering |
| 8–9 | **7. API + app + deploy** | FastAPI, Streamlit, Docker, live link | MLOps |
| 9–10 | **8. Automation + polish** | Scheduled refresh, AI-written red-flag report, README, demo | Communication |

## 5. Roles

- **Owner (you):** product owner, reviewer, learner, presenter. You decide
  scope, run each phase, check the outputs, and own the story.
- **Claude:** writes code, SQL, tests and explanation files; prepares Power BI
  data, DAX and design specs; quizzes you; opens pull requests.

### What you must understand

| Marker | Expectation |
|---|---|
| 🎯 INTERVIEW FOCUS | Explain it AND rebuild it from scratch without AI |
| 📖 READ ONLY | Recognise it; say what it does in one sentence |
| Every decision | Explain *why* (metric, model, cleaning rule) |

Focus order: SQL → EDA/cleaning → model evaluation → Power BI/DAX → the story
→ AI assistant design → (recognise only) Docker, FastAPI setup, CI.

## 6. Power BI: who builds what

Claude cannot operate Power BI Desktop (a Windows GUI app). Claude delivers
star-schema data files, every DAX measure with an explanation, a page-by-page
design spec and a step-by-step build guide, then reviews your screenshots.
**You build the dashboard**, saved as a Power BI Project (`.pbip`) so the model
and measures are text files that can be reviewed in Git. The README will show
screenshots, a PDF export and a short GIF for recruiters.

## 7. Automations

| Automation | Phase |
|---|---|
| One-command pipeline (download → clean → load → build tables) | 1–3 |
| Data quality checks that stop the pipeline on bad data | 1 |
| CI: checks + tests on every push (GitHub Actions) | 0 ✅ |
| Scheduled monthly data refresh (GitHub Actions) | 8 |
| AI-written red-flag summary after each refresh | 8 |
| `CLAUDE.md` project rules followed by every Claude session | 0 ✅ |

Power BI refresh is manual in Power BI Desktop (one click). Scheduled refresh
in the Power BI cloud service needs a work account or paid licence, so it is
not claimed here.

## 8. Tools

Python 3.12, pandas, DuckDB, rapidfuzz, Jupyter, matplotlib/seaborn,
scikit-learn, SHAP, Power BI Desktop, Streamlit, FastAPI, Claude API, pytest,
GitHub Actions, Docker, Git/GitHub, Claude Code in VS Code.
