-- Clean TED contract awards: one row per contract award, typed and labelled.
--
-- Input : {raw_table} (raw text view, several rows per award possible)
-- Output: {output_path} (Parquet) and the view {clean_view}
--
-- Cleaning rules (numbers match the comments below):
--  1. Keep rows that have a contract award ID. Rows without one are lot
--     descriptions with no award section; they carry no award information.
--  2. Drop notices marked as cancelled (TED codebook, section 3.9).
--  3. One row per award ID. An award covering several lots is repeated once
--     per lot with identical award fields; the codebook recommends removing
--     duplicates on the identifier of the level being analysed.
--  4. Convert text to proper types (dates are published as dd/mm/yy).
--  5. Classify each award: awarded, or not awarded (unsuccessful/discontinued).
--  6. Clean the number of offers: 0 and 999 are not plausible counts for an
--     award (999 is a placeholder), so they become unknown (NULL).
--  7. ML label is_single_bid: 1 = one offer, 0 = two or more, NULL = unknown
--     or not awarded.
--  8. Flag implausible award values instead of deleting them, including
--     placeholder values made only of 9s (999,999 ... 999,999,999).
--  9. Several winners in one row are joined with '---': keep the first one
--     and count how many there were.
-- 10. Add readable labels for codes, using the TED codebook and the CPV list.

COPY (
    WITH award_rows AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY id_award
                ORDER BY id_lot NULLS LAST, source_file
            ) AS copy_number
        FROM {raw_table}
        WHERE id_award IS NOT NULL                    -- rule 1
          AND COALESCE(cancelled, '0') <> '1'          -- rule 2
    ),

    one_row_per_award AS (
        SELECT * FROM award_rows
        WHERE copy_number = 1                          -- rule 3
    ),

    typed AS (                                         -- rule 4
        SELECT
            TRY_CAST(id_award AS BIGINT)                          AS award_id,
            TRY_CAST(id_notice_can AS BIGINT)                     AS notice_id,
            TRY_CAST(notice_year AS INTEGER)                      AS notice_year,
            TRY_STRPTIME(dt_dispatch, '%d/%m/%y')::DATE           AS publication_date,
            TRY_STRPTIME(dt_award, '%d/%m/%y')::DATE              AS award_date,
            iso_country_code                                      AS buyer_country,
            cae_name                                              AS buyer_name,
            cae_type                                              AS buyer_type_code,
            main_activity                                         AS buyer_main_activity,
            type_of_contract                                      AS contract_type_code,
            top_type                                              AS procedure_code,
            crit_code                                             AS award_criterion_code,
            yes_no(b_fra_agreement)                               AS is_framework_agreement,
            yes_no(b_eu_funds)                                    AS is_eu_funded,
            yes_no(b_gpa)                                         AS is_gpa_covered,
            yes_no(b_electronic_auction)                          AS used_electronic_auction,
            TRY_CAST(lots_number AS INTEGER)                      AS lots_in_notice,
            cpv                                                   AS cpv_code,
            LEFT(cpv, 2)                                          AS cpv_division,
            TRY_CAST(award_est_value_euro AS DOUBLE)              AS estimated_value_eur,
            TRY_CAST(award_value_euro AS DOUBLE)                  AS award_value_eur,
            TRY_CAST(number_offers AS INTEGER)                    AS number_offers_raw,
            TRY_CAST(number_tenders_sme AS INTEGER)               AS number_offers_from_sme,
            info_on_non_award,
            NULLIF(TRIM(SPLIT_PART(win_name, '---', 1)), '')      AS winner_name,
            standardize_name(win_name)                            AS winner_name_std,
            CASE WHEN NULLIF(TRIM(win_name), '') IS NULL THEN 0
                 ELSE LEN(STRING_SPLIT(win_name, '---'))
            END                                                   AS winner_count,       -- rule 9
            NULLIF(SPLIT_PART(win_country_code, '---', 1), '')    AS winner_country,
            yes_no(SPLIT_PART(b_contractor_sme, '---', 1))        AS winner_is_sme,
            title,
            source_file
        FROM one_row_per_award
    ),

    classified AS (
        SELECT
            *,
            CASE info_on_non_award                                                       -- rule 5
                WHEN 'PROCUREMENT_UNSUCCESSFUL' THEN 'not_awarded_unsuccessful'
                WHEN 'PROCUREMENT_DISCONTINUED' THEN 'not_awarded_discontinued'
                ELSE 'awarded'
            END AS award_status,
            CASE WHEN number_offers_raw BETWEEN 1 AND 998
                 THEN number_offers_raw
            END AS number_offers                                                         -- rule 6
        FROM typed
    )

    SELECT
        classified.* EXCLUDE (info_on_non_award),
        CASE                                                                             -- rule 7
            WHEN award_status <> 'awarded' OR number_offers IS NULL THEN NULL
            WHEN number_offers = 1 THEN 1
            ELSE 0
        END AS is_single_bid,
        CASE                                                                             -- rule 8
            WHEN award_value_eur IS NULL THEN 'missing'
            WHEN REGEXP_MATCHES(CAST(CAST(award_value_eur AS BIGINT) AS VARCHAR), '^9{{6,}}$') THEN 'placeholder'
            WHEN award_value_eur < 100 THEN 'too_low'
            WHEN award_value_eur >= 1e9 THEN 'too_high'
            ELSE 'plausible'
        END AS award_value_quality,
        CASE contract_type_code                                                          -- rule 10
            WHEN 'W' THEN 'Works'
            WHEN 'U' THEN 'Supplies'
            WHEN 'S' THEN 'Services'
        END AS contract_type,
        CASE
            WHEN procedure_code = 'OPE' THEN 'Open'
            WHEN procedure_code = 'RES' THEN 'Restricted'
            WHEN procedure_code IN ('NIC', 'NIP', 'NEC', 'NEG') THEN 'Negotiated with call for competition'
            WHEN procedure_code IN ('NOC', 'NOP') THEN 'Negotiated without call for competition'
            WHEN procedure_code = 'AWP' THEN 'Award without prior publication'
            WHEN procedure_code = 'COD' THEN 'Competitive dialogue'
            WHEN procedure_code = 'INP' THEN 'Innovative partnership'
        END AS procedure_type,
        CASE
            WHEN procedure_code IN ('NOC', 'NOP', 'AWP') THEN FALSE
            WHEN procedure_code IS NULL THEN NULL
            ELSE TRUE
        END AS is_competitive_procedure,
        CASE award_criterion_code
            WHEN 'L' THEN 'Lowest price'
            WHEN 'M' THEN 'Most economically advantageous tender'
        END AS award_criterion,
        CASE buyer_type_code
            WHEN '1' THEN 'National authority'
            WHEN 'N' THEN 'National agency'
            WHEN '3' THEN 'Regional or local authority'
            WHEN 'R' THEN 'Regional or local agency'
            WHEN '4' THEN 'Utilities'
            WHEN '5' THEN 'EU institution or agency'
            WHEN '5A' THEN 'Other international organisation'
            WHEN '6' THEN 'Body governed by public law'
            WHEN '8' THEN 'Other'
            WHEN 'Z' THEN 'Not specified'
        END AS buyer_type,
        cpv.cpv_division_name
    FROM classified
    LEFT JOIN read_csv({cpv_reference_path}, all_varchar = true) AS cpv
        USING (cpv_division)
) TO {output_path} (FORMAT parquet, COMPRESSION zstd);

CREATE OR REPLACE VIEW {clean_view} AS
SELECT * FROM read_parquet({output_path});
