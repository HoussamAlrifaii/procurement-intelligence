# Expected values

Every number below was computed in SQL (DuckDB) on the star schema, using the
same definitions as `powerbi/measures.dax`, with **no slicer selected**. When
the dashboard shows the same values, the model, relationships and measures are
correct.

Data: TED 2019–2022 and World Bank contracts signed 2019–2022, as downloaded on
9 November 2026. The World Bank file is updated daily, so World Bank values
built from a later download can differ slightly.

## Page 1: Overview

| Visual | Measure | Expected |
|---|---|---|
| Card | Award Records | 3,557,158 |
| Card | Awarded Share | 81.0% |
| Card | Single-Bid Rate (Competitive) | 30.6% (2,691,875 labelled awards) |
| Card | Spending (EUR) | €2,691.3 bn |
| Card (optional) | Single-Bid Rate (all procedures) | 32.3% |

**Single-Bid Rate (Competitive) by year** (dim_date[year], visual filter 2019–2022)

| 2019 | 2020 | 2021 | 2022 |
|---:|---:|---:|---:|
| 31.3% | 31.0% | 29.5% | 30.9% |

A few notices dispatched in December 2018 belong to the 2019 files (3,254 labelled
competitive awards at 30.6%); the visual filter hides that partial year.

**Single-Bid Rate (Competitive) by country** (highest and lowest)

| Highest | Rate | Lowest | Rate |
|---|---:|---|---:|
| Slovenia | 59.7% | Iceland | 4.9% |
| Poland | 50.7% | Ireland | 7.3% |
| Czechia | 49.6% | Sweden | 9.0% |
| Greece | 42.8% | Switzerland | 11.2% |
| Hungary | 40.0% | Finland | 11.5% |

**By contract type (competitive):** Supplies 36.1% · Services 25.8% · Works 12.1%

## Page 2: Competition

**Single-Bid Rate by procedure type (all procedures)**

| Procedure | Rate | Labelled awards |
|---|---:|---:|
| Negotiated without call for competition | 86.0% | 79,276 |
| Award without prior publication | 44.2% | 36,117 |
| Innovative partnership | 34.0% | 1,239 |
| Open | 31.1% | 2,469,524 |
| Restricted | 26.4% | 111,740 |
| Negotiated with call for competition | 24.9% | 106,353 |
| Competitive dialogue | 23.6% | 3,019 |
| Not reported | 7.0% | 7,050 |

**By value band (competitive)**

| Under 10k | 10k–100k | 100k–1M | 1M–10M | 10M+ | Unknown |
|---:|---:|---:|---:|---:|---:|
| 37.3% | 34.5% | 27.8% | 19.4% | 11.2% | 23.2% |

**By sector (competitive, highest and lowest of sectors with 10,000+ labelled awards)**

| Sector | Rate |
|---|---:|
| Laboratory, optical and precision equipment | 48.7% |
| Software package and information systems | 39.5% |
| Medical equipment, pharmaceuticals and personal care products | 38.2% |
| … | |
| Architectural, construction, engineering and inspection services | 12.9% |
| Construction work | 12.2% |

**By buyer type (competitive):** Body governed by public law 35.7% · National agency 34.3% ·
Other 33.5% · National authority 29.8% · Regional or local agency 28.0% · Utilities 27.0% ·
Regional or local authority 22.0% · EU institution or agency 16.2%

**Other comparisons (competitive):** EU-funded 38.8% vs not EU-funded 30.0% ·
Lowest price 32.0% vs best value (MEAT) 29.4% · Average Offers (all awards) 5.75

## Page 3: Buyers

| Card | Expected |
|---|---|
| Buyers with 100+ Awards | 4,573 |
| Buyers at 80%+ | 201 |
| Buyers 20+ Points Above Country | 497 |

**Buyers at 80%+ by country:** Slovenia 124 · Czechia 21 · Poland 11 · Romania 8 ·
Bulgaria 6 · Hungary 6

## Page 4: Vendors and markets

| Card | Expected |
|---|---|
| Spending (EUR) | €2,691.3 bn |
| High-Concentration Share | 13.1% (846 of 6,443 eligible buyers) |
| Cross-Market Companies | 672 |
| World Bank Contracts | 136,584 |
| World Bank Spending (USD) | $57.4 bn |

**Top 10 vendors by Spending (EUR)**, axis `dim_vendor[vendor_name]`:

| Vendor | Spending |
|---|---:|
| British Gas | €5.13 bn |
| Budimex S.A. | €4.16 bn |
| Enedis | €4.09 bn |
| ALLIANCE HEALTHCARE ROMANIA | €3.90 bn |
| Enel Energia S.p.A. | €3.90 bn |
| Keolis | €3.57 bn |
| Leonardo S.p.A. | €3.25 bn |
| Atea Sverige AB | €2.93 bn |
| Serco Ltd | €2.78 bn |
| Skanska Sverige AB | €2.59 bn |

Power BI groups an axis by the displayed name, so vendor records that share a
display name (for example the same company registered in two countries) are
added together. Leonardo S.p.A. reaches the top 10 this way.

**Cross-market companies by World Bank Spending (USD):** Moderna Switzerland GmbH (CH) $788.4 m ·
Sinohydro Corporation Limited (CN) $785.1 m · BioNTech Manufacturing GmbH (DE) $749.4 m ·
Acciona Agua, S. A. (ES) $251.2 m · Pfizer Export B.V. (NL) $174.7 m
