# Phase 3: Star schema and SQL analysis

**Goal:** reorganise the clean data into a star schema for analysis and Power
BI, and answer the main business questions with SQL.

```bash
python -m procurement.pipeline --skip-download   # step 6 builds the star schema
python -m procurement.analysis                   # runs sql/analysis/*.sql, saves CSV to data/analysis/
```

Results with charts and findings: [`notebooks/03_sql_analysis.ipynb`](../../notebooks/03_sql_analysis.ipynb).

## 1. The star schema

```
                 dim_buyer (99,679)          dim_vendor (555,443)
                          \                  /          \
dim_date (1,492) —— fact_award (3,557,158) —— dim_sector (45)    fact_world_bank_contract (142,870)
                          |                                       /
                 dim_procedure (10)                    dim_date, dim_vendor
```

| Table | Grain (one row = …) | Key | Built by |
|---|---|---|---|
| `fact_award` | one TED contract award record (awarded or not) | `award_id` | `sql/marts/06_fact_award.sql` |
| `fact_world_bank_contract` | one supplier on one World Bank contract | — | `sql/marts/07_fact_world_bank_contract.sql` |
| `dim_buyer` | one buyer (standardised name + country) | `buyer_key` | `04_dim_buyer.sql` |
| `dim_vendor` | one company (standardised name + country), **shared by both facts** | `vendor_key` | `05_dim_vendor.sql` |
| `dim_sector` | one CPV division | `sector_key` | `02_dim_sector.sql` |
| `dim_procedure` | one procedure code | `procedure_key` | `03_dim_procedure.sql` |
| `dim_date` | one calendar day | `date_key` (YYYYMMDD) | `01_dim_date.sql` |

Each table is written to `data/marts/<table>.parquet` (the files Power BI
loads) and exposed as a DuckDB view.

### Design decisions

1. **Dimensions connect only to facts, never to each other.** A query joins
   the fact table to the dimensions it needs; Power BI does the same through
   relationships drawn once.
2. **Surrogate keys.** `buyer_key` and `vendor_key` are small integers created
   in the dimension and looked up by the fact table. They are faster to join
   than long text names and decouple the fact table from naming rules.
3. **Natural keys for matching.** Buyers and vendors are identified by
   standardised name **and** country, so different spellings merge while
   unrelated organisations with similar names in other countries do not.
4. **No row lost.** The fact table is built with `LEFT JOIN`s, so it has
   exactly as many rows as the clean table (3,557,158). Tests check this and
   that every key exists in its dimension.
5. **A galaxy schema.** Two fact tables share `dim_vendor` and `dim_date`. This
   is how a company's EU and World Bank activity are compared.
6. **All award records in the fact table**, awarded or not, with
   `award_status` and `is_awarded`, so dashboards can show failed tenders
   as well as single bids.
7. **`award_value_eur_plausible`.** The value only when it passed the quality
   checks, so `SUM()` in SQL or Power BI never includes flagged values.

## 2. The business questions

| File | Question | Technique |
|---|---|---|
| `01_single_bid_trend_by_country.sql` | How does the single-bid rate change each year per country? | `GROUP BY`, `LAG()` |
| `02_buyer_red_flags.sql` | Which buyers (100+ awards) have the highest single-bid rates? | CTEs, `HAVING`, `RANK()` |
| `03_buyer_concentration.sql` | How concentrated is each buyer's spending? | window shares, HHI |
| `04_repeat_single_bid_pairs.sql` | Which buyer–vendor pairs repeat single-bid wins? | aggregation on a key pair |
| `05_sector_top_vendors.sql` | Which vendors lead each sector? | `SUM() OVER`, `ROW_NUMBER()` |
| `06_price_anomalies.sql` | Which awards are priced far above similar ones? | `QUANTILE_CONT() OVER`, Tukey rule on log values |
| `07_cross_market_vendors.sql` | Which companies win in both markets? | two facts through one dimension |

Single-bid analyses use **competitive procedures** only (Phase 2 decision).
Value analyses exclude **framework agreements**: their published value is a
ceiling for future orders, not spending. They are 18% of priced awards but
about half of all published value.

## 3. Main results

- Single bidding rose in **22 of 33** countries between 2019 and 2022; Poland (51.9%), Czechia (50.7%) and Slovenia (50.2%) were highest in 2022.
- **201** buyers with 100+ awards have a single-bid rate of 80% or more; 124 are in Slovenia, 80 of them schools or kindergartens.
- **13.1%** of buyers have highly concentrated spending (HHI ≥ 2,500); in 603 buyers one vendor receives over half the value.
- **4,459** buyer–vendor pairs share 20+ single-bid wins.
- The three largest vendors take a median **9.6%** of a sector's spending.
- **0.82%** of priced awards are log-scale outliers within their group.
- **672** companies win in both markets.

All are risk indicators and descriptions, not evidence of wrongdoing.

## 4. Data issues found while building the schema

Building and checking the star schema exposed three problems in the earlier
layers, which were fixed:

| Issue | How it was found | Fix |
|---|---|---|
| Names in Cyrillic and Greek became empty after standardisation (128,362 buyer names, 81,129 winner names, mostly Bulgaria, Greece, Cyprus) | 128,362 fact rows had no `buyer_key` | `standardize_name()` keeps letters of every alphabet (`\p{L}`) and removes Bulgarian and Greek legal forms |
| 647 award values made only of 9s (e.g. 999,999,999) passed as plausible | Sector leaders with totals of exactly EUR 1,999,999,998 | New flag `award_value_quality = 'placeholder'` |
| Joint purchases displayed several buyer names joined with `---` | Buyer ranking output | The display name keeps the lead buyer, consistent with the standardised key |

## 5. Tests

`tests/test_marts.py` builds the schema from the synthetic fixtures and checks
that the fact table keeps every award, dimension keys are unique, every fact
key exists in its dimension, vendor keys are missing only when there is no
winner, a company shared by both sources is one vendor, flagged values are
excluded from `award_value_eur_plausible`, and every analysis query runs.

## 6. Data published in the notebook

Public buyers are named. Vendor names are omitted from the buyer–vendor pair
results in the notebook, because some vendors are individuals and a named pair
next to "repeat single-bid wins" could be misread. The full results are saved
locally in `data/analysis/` (not committed).
