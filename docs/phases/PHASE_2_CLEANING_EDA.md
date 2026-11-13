# Phase 2: Cleaning and exploratory data analysis

**Goal:** turn the raw text tables into clean, typed, de-duplicated tables, and
understand the data well enough to decide how later phases use it.

```bash
python -m procurement.pipeline --skip-download   # rebuilds everything, including the clean layer
python -m procurement.clean                      # clean layer only (raw layer must exist)
```

Then open [`notebooks/02_eda.ipynb`](../../notebooks/02_eda.ipynb).

## 1. What was built

| File | Purpose |
|---|---|
| `sql/clean/clean_ted_awards.sql` | All TED cleaning rules, numbered 1–10 |
| `sql/clean/clean_world_bank_awards.sql` | World Bank cleaning rules, numbered 1–4 |
| `sql/clean/macros.sql` | Shared SQL functions: `standardize_name()` and `yes_no()` |
| `reference/cpv_divisions.csv` | Names of the 45 CPV sector divisions |
| `procurement/clean.py` | Runs the cleaning SQL; step 5 of the pipeline |
| `notebooks/02_eda.ipynb` | Exploratory analysis: questions, charts and written findings |
| `tests/test_clean.py` | Tests every cleaning rule on synthetic rows |

Data layers after this phase:

```
raw layer (text, as published)          clean layer (typed, one row per unit)
raw_ted_awards         4,295,572 rows   ted_awards          3,557,158 rows  one per contract award
raw_world_bank_awards    142,870 rows   world_bank_awards     142,870 rows  one per supplier on a contract
```

## 2. TED cleaning rules

The grain of the clean table is **one contract award**, the level at which
TED records the number of offers.

| # | Rule | Why | Rows affected |
|---|---|---|---:|
| 1 | Keep rows with an award ID | Rows without one describe a lot but have no award section (codebook §3.7) | 667,385 removed |
| 2 | Drop cancelled notices | Recommended by the codebook (§3.9) | 4 removed |
| 3 | One row per award ID | An award covering several lots is repeated per lot with identical award fields; the codebook recommends de-duplicating on the identifier of the level analysed (§3.6) | 71,025 removed |
| 4 | Convert types | Dates (`dd/mm/yy`) become `DATE`, numbers become `INTEGER`/`DOUBLE` | all |
| 5 | `award_status` | `awarded`, `not_awarded_unsuccessful` (no valid offers) or `not_awarded_discontinued` | 677,416 not awarded |
| 6 | Clean `number_offers` | 0 offers on an award and the value 999 (a placeholder) are not plausible counts, so they become unknown | 1,879 values (165 zeros, 1,714 placeholders) |
| 7 | `is_single_bid` | 1 = one offer, 0 = two or more, NULL = unknown or not awarded | 2,814,318 labelled |
| 8 | `award_value_quality` | `too_low` (< EUR 100), `too_high` (≥ EUR 1 bn), `placeholder` (only 9s, e.g. 999,999,999), `missing` or `plausible`; values are flagged, never deleted | 262,356 awarded contracts flagged |
| 9 | Several winners | Names joined with `---`: keep the first (as the codebook describes) and record `winner_count` | 239,554 awards |
| 10 | Readable labels | Contract type, procedure, criterion and buyer type from the codebook; sector names from the CPV list | all |

Check: 4,295,572 raw rows − 667,385 − 4 − 71,025 = **3,557,158** clean rows,
which equals the number of distinct non-cancelled award IDs.

## 3. World Bank cleaning rules

The grain is **one supplier on one contract**: joint ventures have one row per
partner, which supplier analysis needs.

| # | Rule | Why |
|---|---|---|
| 1 | Convert types | Dates (`mm/dd/yyyy`) and amounts |
| 2 | `amount_usd_for_totals` | When every partner row of a contract shows the same amount, it is the contract total repeated, so it counts once. When amounts differ, each row is that partner's share. Without this, totals would include **USD 4.4 bn (7.7%) of double counting**. |
| 3 | `supplier_name_std` | Same name standardisation as TED winners, so the sources can be linked |
| 4 | `amount_quality` | Amounts below USD 100 are flagged |

## 4. Vendor-name standardisation

`standardize_name()` (in `sql/clean/macros.sql`): keep the first name, lowercase,
remove accents, replace punctuation with spaces, remove legal-form words
(GmbH, Ltd, S.A., Sp. z o.o., S.L.U. …), collapse spaces.

| Raw name | Standardised |
|---|---|
| Siemens Healthcare Sp. z o.o. | siemens healthcare |
| SIEMENS HEALTHCARE, S.L.U. | siemens healthcare |
| Siemens Healthcare, s.r.o. | siemens healthcare |

This reduces distinct winner names from 720,095 to 480,403 (−33.3%). Letters of every alphabet are kept, so Bulgarian (Cyrillic) and Greek names are standardised too.
**Option chosen:** a transparent rule rather than fuzzy matching. Fuzzy
matching would catch spelling mistakes, but risks merging unrelated companies
and is hard to explain or audit. It can be added later if Phase 3 needs it.

## 5. How the two sources are linked

The sources describe different markets (EU public buyers vs World
Bank-financed projects in borrower countries), so there is **no shared
contract or tender ID**. They are linked through the **company**:

```sql
-- EU winners and World Bank suppliers with the same standardised name AND country
SELECT name_std, country, eu_awards, world_bank_contracts
FROM eu_winners
INNER JOIN world_bank_suppliers USING (name_std, country);
```

Requiring the same country prevents merging unrelated companies with similar
names. Result: 672 companies won contracts in both markets in 2019–2022, a
conservative lower bound.

## 6. Key EDA findings

Full analysis with charts: [`notebooks/02_eda.ipynb`](../../notebooks/02_eda.ipynb).

- 32.3% of labelled awards received one offer (2,814,318 labelled awards).
- Missing offer counts are structural: 95% are lot rows without an award section or lots never awarded.
- Non-competitive procedures are single-bid 86% of the time by design; competitive procedures 30.6%.
- Single-bid rates range from 60% (Slovenia) to 6% (Iceland); 52% for laboratory equipment vs 14% for construction work; 38% under EUR 10k vs 14% above EUR 10M.
- 9% of award values are below EUR 100, concentrated in Germany and the Netherlands and often linked to framework agreements.

All rates are descriptive associations; a high single-bid rate is a risk
indicator, not evidence of wrongdoing.

## 7. Decisions for the next phases

| Finding | Decision |
|---|---|
| 97.7% of awarded contracts have a valid label | `is_single_bid` is the ML target |
| Non-competitive procedures are single-bid by design | Phase 5 trains on competitive procedures only |
| Final award value is only known after the tender | Not used as a model feature (leakage) |
| Award counts differ from money | Phase 3 measures vendor concentration by value and count |
| The sources connect through companies | Phase 3 builds a vendor dimension on `(name_std, country)` |

## 8. Tests

`tests/test_clean.py` builds the clean layer from synthetic fixtures
(`tests/fixtures/ted_clean_sample.csv`, `world_bank_clean_sample.csv`) and
checks every rule: de-duplication, cancelled and lot-only rows, the
single-bid label including the 0 and 999 cases, value flags, labels, multiple
winners, name standardisation, and the joint-venture amount rule.
