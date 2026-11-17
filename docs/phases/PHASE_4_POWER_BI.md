# Phase 4: Power BI dashboard

**Goal:** a four-page Power BI report that tells one story, *where public
procurement competition fails and where to look first*, for three audiences:
procurement officers, auditors and small businesses.

| File | Purpose |
|---|---|
| `powerbi/measures.dax` | All DAX measures, added in one step through DAX query view |
| `powerbi/theme_ocean_night.json` | **Report theme used** (Ocean Night): blue data, pink highlights on deep navy (colour-blind-safe, validated on the navy surface) |
| `powerbi/theme.json` | Light alternative with the same structure (blue and orange) |
| `powerbi/expected_values.md` | The value every visual must show with no slicer selected |
| `data/marts/*.parquet` | The star schema (built by `python -m procurement.pipeline`) |

---

## Part 1: Model setup (about 30 minutes)

### 1.1 Report settings
- **File → Options and settings → Options → Current file → Data load:** turn **off** *Auto date/time* (the model has its own date table).
- **Current file → Report settings:** turn on *Use the modern visual header*.

### 1.2 Folder parameter (portable data source)
Home → Transform data → **Manage parameters → New**:

| Name | Type | Current value |
|---|---|---|
| `DataFolder` | Text | the full path to `data\marts\` with a trailing backslash, e.g. `C:\Users\<you>\Projects\procurement-intelligence\data\marts\` |

### 1.3 Load the seven tables
In Power Query: **New Source → Blank Query** for each table, open the
**Advanced Editor**, paste, and name the query exactly as the table:

```powerquery
let
    Source = Parquet.Document(File.Contents(DataFolder & "fact_award.parquet"))
in
    Source
```

Repeat with `fact_world_bank_contract`, `dim_buyer`, `dim_vendor`, `dim_sector`,
`dim_procedure`, `dim_date`. Check the column types Power Query detects:
keys and `date_key` are whole numbers, `dim_date[date]` is Date, flags such as
`is_competitive` and `in_ted` are True/False, values are decimal numbers.
Then **Close & Apply**.

### 1.4 Relationships (Model view)
All are many-to-one, single direction (dimension filters fact):

| From (many) | To (one) |
|---|---|
| `fact_award[date_key]` | `dim_date[date_key]` |
| `fact_award[buyer_key]` | `dim_buyer[buyer_key]` |
| `fact_award[vendor_key]` | `dim_vendor[vendor_key]` |
| `fact_award[sector_key]` | `dim_sector[sector_key]` |
| `fact_award[procedure_key]` | `dim_procedure[procedure_key]` |
| `fact_world_bank_contract[date_key]` | `dim_date[date_key]` |
| `fact_world_bank_contract[vendor_key]` | `dim_vendor[vendor_key]` |

`dim_vendor` and `dim_date` are shared by both fact tables (a galaxy schema).
Do not create any relationship between the two fact tables.

### 1.5 Model properties
- **Mark `dim_date` as the date table** on `dim_date[date]` (Table tools → Mark as date table). Time-intelligence measures need this.
- **Sort by column:** `dim_date[month_name]` by `dim_date[month]`; `fact_award[value_band]` by `fact_award[value_band_order]`.
- **Data category:** `dim_buyer[buyer_country_name]` = *Country/Region*.
- **Hide** every `*_key` column, `value_band_order`, `buyer_name_std`, `vendor_name_std`, and the raw value columns of both fact tables (`award_value_eur`, `award_value_eur_plausible`, `spend_value_eur`, `amount_usd`, `amount_usd_for_totals`): visuals use the measures instead.
- **Summarize by: None** for `dim_date[year]`, `quarter`, `month`, and every key.

### 1.6 Measures
1. Home → **Enter data** → table name `_Measures` → Load.
2. Open **DAX query view**, paste `powerbi/measures.dax`, and click **Update model: Add new measures**.
3. Delete `Column1` from `_Measures` (it becomes a measure table).
4. Set each measure's format from the comment next to it, and group them into display folders: *Volume*, *Competition*, *Buyers*, *Spending and vendors*, *World Bank*, *Formatting*.
5. Run the `EVALUATE` at the end of the file: it should return 3,557,158 · 0.306 · 2.69e12 · 672.

### 1.7 Theme
Design → **Import theme** → `powerbi/theme_ocean_night.json` (the conditional-formatting measures return blue `#2B8DE0` and pink `#E4528A`).

---

## Part 2: Design system (applies to every page)

**Canvas:** 1280 × 720 (16:9). Margins 24 px; gaps between visuals 16 px.

**Colour rules (the theme sets these):**

| Colour | Meaning | Use |
|---|---|---|
| Blue `#2A78D6` | the data | every bar and line by default |
| Orange `#EB6834` | needs attention | values above the reference (e.g. above the all-countries rate) |
| Grey `#52514E` | context | reference lines, secondary text |
| Page `#F5F5F3`, cards `#FFFFFF` | structure | soft page, white visual cards with 8 px radius |

Use **one colour per chart** unless colour carries meaning (above/below
average, competitive or not). Never use colour as the only signal: keep
**data labels on** for every bar chart (three palette colours are below 3:1
contrast on white, and labels make every value readable).

**Typography:** page title 20 pt Segoe UI Semibold; subtitle 11 pt Segoe UI
`#52514E`; visual titles 12 pt (theme); data labels 9 pt.

**Titles say the insight, not the field.** Write *"Small contracts attract
single bids three times as often as large ones"*, not *"Rate by value band"*.

**Standard header on every page (top 96 px):**

| Element | Position (x, y, width, height) | Content |
|---|---|---|
| Title text box | 24, 16, 760, 40 | page story title |
| Subtitle text box | 24, 52, 760, 28 | one sentence of context |
| Slicers | 800–1256, 20 | Year (dropdown), Country (dropdown with search) |

Sync the Year and Country slicers across all pages (View → Sync slicers).

**Footer on every page (y = 696):** text box, 8 pt grey: *"Source: TED (EU) and
World Bank contract awards, 2019–2022. Single-bid rate = share of awards with
one offer, competitive procedures. A risk indicator, not evidence of wrongdoing."*

---

## Part 3: The pages

### Page 1: Overview
**Story:** *one in three competitive tenders gets a single offer, and it depends heavily on where you are.*

| # | Visual | Position | Fields | Formatting |
|---|---|---|---|---|
| 1 | Card (new), 4 callouts | 24, 104, 1232, 120 | Award Records · Awarded Share · Single-Bid Rate (Competitive) · Spending (EUR) | Callout labels: "Award records", "Awarded", "Single-bid rate (competitive)", "Spending (excl. frameworks)" |
| 2 | Line chart | 24, 240, 600, 220 | X: `dim_date[year]` · Y: Single-Bid Rate (Competitive) | Visual filter year 2019–2022; markers on; data labels on; Y axis from 0% to 40% |
| 3 | Clustered bar chart | 640, 240, 616, 440 | Y: `dim_buyer[buyer_country_name]` · X: Single-Bid Rate (Competitive) | Sort descending; bar colour **fx** → Field value → `Bar Colour vs Average`; Analytics → constant line = **fx** `Single-Bid Rate (All Countries)`, grey dashed, label "All countries"; data labels on |
| 4 | Clustered bar chart | 24, 476, 600, 204 | Y: `fact_award[contract_type]` · X: Single-Bid Rate (Competitive) | Same colour rule and constant line as visual 3 |

**Title:** use the `Title Overview` measure (Format → Title → **fx** → Field value),
or the static *"One in three competitive EU tenders receives a single offer"*.

**Subtitle:** *"3.56 million contract awards in 33 European countries, 2019–2022. Orange = above the all-countries rate."*

### Page 2: Competition
**Story:** *what makes a tender attract only one bidder?* (for procurement officers)

| # | Visual | Position | Fields | Formatting |
|---|---|---|---|---|
| 1 | Clustered bar chart | 24, 104, 600, 280 | Y: `dim_procedure[procedure_type]` · X: Single-Bid Rate (**all procedures**) | Title: *"Without a call for competition, 86% of awards get one offer"*; bar colour **fx** → Field value → `Procedure Bar Colour` (orange = no call for competition); data labels on |
| 2 | Clustered column chart | 640, 104, 616, 280 | X: `fact_award[value_band]` · Y: Single-Bid Rate (Competitive) | Visual filter: value_band ≠ Unknown; sorted by value band; data labels; title: *"Small contracts attract single bids three times as often as large ones"* |
| 3 | Clustered bar chart | 24, 400, 600, 280 | Y: `dim_sector[sector_name]` · X: Single-Bid Rate (Competitive) | Visual filter: Top N 15 by Labelled Awards (Competitive); sort by rate; colour rule `Bar Colour vs Average`; title: *"Medical, maintenance and transport supplies lead; construction is lowest"* |
| 4 | Clustered bar chart | 640, 400, 400, 280 | Y: `dim_buyer[buyer_type]` · X: Single-Bid Rate (Competitive) | Visual filter: Labelled Awards (Competitive) ≥ 1,000; data labels |
| 5 | Card (new), 2 callouts | 1056, 400, 200, 280 | Average Offers · Labelled Awards (Competitive) | Stacked vertically |

**Slicers on this page (in the header):** add `fact_award[contract_type]` (tile style) next to Year and Country.

### Page 3: Buyers
**Story:** *where should an auditor look first?*

| # | Visual | Position | Fields | Formatting |
|---|---|---|---|---|
| 1 | Card (new), 3 callouts | 24, 104, 1232, 100 | Buyers with 100+ Awards · Buyers at 80%+ · Buyers 20+ Points Above Country | Title: `Title Buyers` measure |
| 2 | Scatter chart | 24, 220, 600, 460 | Values: `dim_buyer[buyer_name]` · X: Labelled Awards (Competitive) · Y: Single-Bid Rate (Competitive) | Visual filter: Labelled Awards (Competitive) ≥ 100; X axis **logarithmic**; marker colour **fx** → Gradient on `Gap vs Country` (min `#2A78D6`, centre 0 `#E6E5E0`, max `#E34948`); title: *"Each dot is a buyer: higher = more single bids"* |
| 3 | Table | 640, 220, 616, 300 | `dim_buyer[buyer_name]`, `dim_buyer[buyer_country_name]`, `dim_buyer[buyer_type]`, Labelled Awards (Competitive), Single-Bid Rate (Competitive), Country Single-Bid Rate, Gap vs Country | Visual filter: Labelled Awards (Competitive) ≥ 100; sort by rate descending; Gap vs Country → background colour gradient (blue → grey → red, centre 0); rate → data bars in blue |
| 4 | Clustered bar chart | 640, 536, 616, 144 | Y: `dim_buyer[buyer_country_name]` · X: Buyers at 80%+ | Top N 6 by Buyers at 80%+; data labels; title: *"Most high-rate buyers are in Slovenia"* |

Add a text box under the title: *"A high rate is a reason to look closer, not proof
of wrongdoing. In Slovenia, 80 of 124 high-rate buyers are schools and kindergartens."*

### Page 4: Vendors and markets
**Story:** *who wins the money, and how concentrated is it?*

| # | Visual | Position | Fields | Formatting |
|---|---|---|---|---|
| 1 | Card (new), 4 callouts | 24, 104, 1232, 100 | Spending (EUR) · High-Concentration Share · Cross-Market Companies · World Bank Spending (USD) | Callout labels: "Spending (excl. frameworks)", "Buyers with high concentration", "Companies in both markets", "World Bank spending" |
| 2 | Clustered bar chart | 24, 220, 600, 300 | Y: `dim_vendor[vendor_name]` · X: Spending (EUR) | Top N 10 by Spending (EUR); data labels €#,0.00,,,"bn"; title: *"The largest suppliers are utilities, construction and healthcare"*. The axis groups by display name, so records sharing a name are added together |
| 3 | Table | 640, 220, 616, 300 | `dim_buyer[buyer_name]`, `dim_buyer[buyer_country_name]`, Priced Awards, Vendors Paid, Top Vendor Share, HHI, Concentration Band | Visual filter: Priced Awards ≥ 50; sort by HHI descending; HHI → icons or background by rules (≥ 2,500 orange, 1,500–2,500 yellow, below grey) |
| 4 | Clustered bar chart | 24, 536, 1232, 144 | Y: `dim_vendor[vendor_name]` · X: World Bank Spending (USD) | Visual filters: `dim_vendor[in_ted]` = True and `dim_vendor[in_world_bank]` = True; Top N 8 by World Bank Spending (USD); title: *"Companies winning in both markets include COVID-19 vaccine makers"* |

Add a slicer for `dim_sector[sector_name]` (dropdown) in the header on this page.

---

## Part 4: Check, save and publish

1. **Check every visual against `powerbi/expected_values.md`** (no slicers selected). A mismatch means a relationship, a filter direction or a measure needs fixing.
2. **Save as a Power BI project:** File → Save as → *Power BI project (.pbip)* → `powerbi/ProcurementIntelligence.pbip`. The project stores the model and measures as text files, so it can be committed and reviewed. The imported data cache is excluded by `.gitignore`.
3. **Screenshots:** one PNG per page (File → Export → or a full-screen capture) saved as `docs/images/dashboard_1_overview.png` … `dashboard_4_vendors.png`.
4. **PDF export:** File → Export → Export to PDF → `reports/dashboard.pdf`.
5. Commit on branch `phase-4-power-bi` and open a pull request; the README will then show the screenshots.

## Notes and limits

- `fact_award` has 3.56 million rows; the import takes a few minutes and the file is roughly 100–200 MB. Measures that rank buyers (`Buyers at 80%+`, `High-Concentration Share`) iterate over all buyers and may take a few seconds when no slicer is selected.
- The `DataFolder` parameter holds a local path. Anyone opening the project sets it to their own copy of `data\marts\`.
- Value measures exclude framework agreements and implausible values, so "Spending" is a conservative estimate of actual awarded spending, not total market size.
