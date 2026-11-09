# Raw data profile

Generated 2026-11-09 by `python -m procurement.pipeline`. "Filled" means neither missing nor blank. All raw columns are stored as text.

## Source files

| File | Size (MB) | Downloaded (UTC) | SHA-256 (first 12) |
|---|---:|---|---|
| `ted-contract-award-notices-2019.zip` | 86.6 | 2026-11-09T19:59:54+00:00 | `9ddf374dca7c` |
| `ted-contract-award-notices-2020.zip` | 88.5 | 2026-11-09T19:59:58+00:00 | `83534fc58d02` |
| `ted-contract-award-notices-2021.zip` | 98.2 | 2026-11-09T20:00:04+00:00 | `f6c6c6f2d7dd` |
| `ted-contract-award-notices-2022.zip` | 101.5 | 2026-11-09T20:00:09+00:00 | `eb3aa7c2eb0c` |
| `world_bank_contract_awards.csv` | 115.4 | 2026-11-09T20:00:14+00:00 | `ae6d3931ddf9` |

## `raw_ted_awards`

4,295,572 rows, 76 columns.

| Column | Filled | Distinct values | Most frequent values |
|---|---:|---:|---|
| `id_notice_can` | 100.0% | 1,118,490 |  |
| `ted_notice_url` | 100.0% | 1,118,490 |  |
| `notice_year` | 100.0% | 4 | 2021 27%, 2022 25%, 2020 25%, 2019 23% |
| `id_type` | 100.0% | 7 | 3 92%, 6 6%, 21 2%, 18 0%, 25 0% |
| `dt_dispatch` | 100.0% | 1,463 |  |
| `xsd_version` | 100.0% | 5 | R209.S3 53%, R209.S5 28%, R209.S4 19%, R208.S4 0%, R208.S5 0% |
| `cancelled` | 100.0% | 2 | 0 100%, 1 0% |
| `corrections` | 100.0% | 6 | 0 100%, 1 0%, 2 0%, 4 0%, 5 0% |
| `b_multiple_cae` | 99.5% | 2 | N 96%, Y 3%, (blank) 0% |
| `cae_name` | 100.0% | 153,503 |  |
| `cae_nationalid` | 66.2% | 51,421 |  |
| `cae_address` | 98.3% | 144,306 |  |
| `cae_town` | 100.0% | 44,498 |  |
| `cae_postal_code` | 98.0% | 50,005 |  |
| `cae_gpa_annex` | 100.0% | 4 | A2    79%, A1    12%, A3    7%, OUT   2% |
| `iso_country_code` | 100.0% | 33 |  |
| `iso_country_code_gpa` | 100.0% | 34 |  |
| `b_multiple_country` | 99.5% | 2 | N 99%, (blank) 0%, Y 0% |
| `iso_country_code_all` | 0.1% | 307 |  |
| `cae_type` | 100.0% | 10 | 6 31%, 8 27%, 3 20%, 1 11%, 4 6% |
| `eu_inst_code` | 0.2% | 14 | (blank) 100%, AG 0%, EC 0%, PA 0%, BC 0% |
| `main_activity` | 100.0% | 52 |  |
| `b_on_behalf` | 100.0% | 2 | N 92%, Y 8%, (blank) 0% |
| `b_involves_joint_procurement` | 99.4% | 2 | N 96%, Y 3%, (blank) 1% |
| `b_awarded_by_central_body` | 99.4% | 2 | N 94%, Y 5%, (blank) 1% |
| `type_of_contract` | 100.0% | 3 | U 62%, S 31%, W 7% |
| `tal_location_nuts` | 96.7% | 21,653 |  |
| `b_fra_agreement` | 100.0% | 2 | N 84%, Y 16% |
| `fra_estimated` | 27.9% | 7 | (blank) 72%, A 12%, K 9%, KA 6%, C 0% |
| `b_fra_contract` | 100.0% | 2 | N 61%, Y 39% |
| `b_dyn_purch_syst` | 94.7% | 2 | N 94%, (blank) 5%, Y 1% |
| `cpv` | 100.0% | 7,512 |  |
| `main_cpv_code_gpa` | 100.0% | 3,304 |  |
| `id_lot` | 75.5% | 28,386 |  |
| `additional_cpvs` | 87.1% | 183,449 |  |
| `b_gpa` | 94.8% | 2 | N 58%, Y 37%, (blank) 5% |
| `gpa_coverage` | 100.0% | 6 | 1 60%, 4 25%, 3 8%, 6 5%, 5 2% |
| `lots_number` | 99.8% | 398 |  |
| `value_euro` | 91.2% | 607,457 |  |
| `value_euro_fin_1` | 91.3% | 665,087 |  |
| `value_euro_fin_2` | 91.3% | 664,860 |  |
| `b_eu_funds` | 97.1% | 2 | N 91%, Y 7%, (blank) 3% |
| `top_type` | 99.8% | 9 | OPE 89%, NIC 4%, RES 3%, NOC 2%, AWP 1% |
| `b_accelerated` | 2.2% | 1 | (blank) 98%, Y 2% |
| `out_of_directives` | 100.0% | 2 | 0 99%, 1 1% |
| `crit_code` | 93.4% | 2 | L 55%, M 39%, (blank) 7% |
| `crit_price_weight` | 28.0% | 6,898 |  |
| `crit_criteria` | 39.0% | 282,197 |  |
| `crit_weights` | 38.8% | 73,019 |  |
| `b_electronic_auction` | 97.8% | 2 | N 95%, Y 3%, (blank) 2% |
| `number_awards` | 100.0% | 735 |  |
| `id_award` | 84.5% | 3,557,162 |  |
| `id_lot_awarded` | 63.0% | 62,346 |  |
| `info_on_non_award` | 16.0% | 2 | (blank) 84%, PROCUREMENT_UNSUCCESSFUL 13%, PROCUREMENT_DISCONTINUED 3% |
| `info_unpublished` | 100.0% | 2 | N 98%, Y 2% |
| `b_awarded_to_a_group` | 65.2% | 2 | N 60%, (blank) 35%, Y 6% |
| `win_name` | 67.5% | 806,047 |  |
| `win_nationalid` | 32.4% | 232,993 |  |
| `win_address` | 51.6% | 583,781 |  |
| `win_town` | 67.5% | 193,566 |  |
| `win_postal_code` | 52.5% | 175,304 |  |
| `win_country_code` | 67.5% | 4,200 |  |
| `b_contractor_sme` | 67.1% | 2,919 |  |
| `contract_number` | 52.6% | 627,147 |  |
| `title` | 69.3% | 1,771,171 |  |
| `number_offers` | 66.9% | 397 |  |
| `number_tenders_sme` | 38.5% | 278 |  |
| `number_tenders_other_eu` | 30.9% | 72 |  |
| `number_tenders_non_eu` | 30.6% | 54 |  |
| `number_offers_electr` | 40.8% | 322 |  |
| `award_est_value_euro` | 34.1% | 680,195 |  |
| `award_value_euro` | 66.8% | 1,397,965 |  |
| `award_value_euro_fin_1` | 82.9% | 1,398,086 |  |
| `b_subcontracted` | 68.2% | 2 | N 65%, (blank) 32%, Y 3% |
| `dt_award` | 67.4% | 2,790 |  |
| `source_file` | 100.0% | 4 | ted-contract-award-notices-2021.zip 27%, ted-contract-award-notices-2022.zip 25%, ted-contract-award-notices-2020.zip 25%, ted-contract-award-notices-2019.zip 23% |

## `raw_world_bank_awards`

142,870 rows, 22 columns.

| Column | Filled | Distinct values | Most frequent values |
|---|---:|---:|---|
| `as_of_date` | 100.0% | 1 | 11/09/2026 100% |
| `fiscal_year` | 100.0% | 4 | 2021 31%, 2022 29%, 2020 25%, 2023 15% |
| `region` | 100.0% | 8 | Eastern and Southern Africa 21%, Western and Central Africa 20%, South Asia 20%, Latin America and Caribbean 15%, East Asia and Pacific 11% |
| `borrower_country_economy` | 100.0% | 153 |  |
| `borrower_country_economy_code` | 97.1% | 142 |  |
| `project_id` | 100.0% | 2,317 |  |
| `project_name` | 100.0% | 2,304 |  |
| `project_global_practice` | 93.6% | 219 |  |
| `procurement_category` | 100.0% | 4 | Consultant Services 38%, Goods 32%, Works 21%, Non-consulting Services 8% |
| `procurement_method` | 100.0% | 19 | Request for Quotations 35%, Individual Consultant Selection 23%, Request for Bids 18%, Direct Selection 13%, Consultant Qualification  Selection 5% |
| `wb_contract_number` | 100.0% | 136,584 |  |
| `contract_description` | 99.8% | 122,601 |  |
| `borrower_contract_reference_number` | 100.0% | 127,163 |  |
| `contract_signing_date` | 100.0% | 1,280 |  |
| `supplier_id` | 100.0% | 96,231 |  |
| `supplier` | 100.0% | 65,262 |  |
| `supplier_country_economy` | 100.0% | 222 |  |
| `supplier_country_economy_code` | 100.0% | 222 |  |
| `supplier_contract_amount_usd` | 100.0% | 115,458 |  |
| `review_type` | 100.0% | 2 | Post 93%, Prior 7%, (blank) 0% |
| `contract_signed_calendar_year` | 100.0% | 4 | 2021 30%, 2020 30%, 2022 29%, 2019 11% |
| `source_file` | 100.0% | 1 | world_bank_contract_awards.csv 100% |
