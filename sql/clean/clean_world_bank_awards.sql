-- Clean World Bank contract awards: one row per supplier on a contract.
--
-- Input : {raw_table}    Output: {output_path} (Parquet) and the view {clean_view}
--
-- Cleaning rules:
--  1. Convert text to proper types (signing dates are published as mm/dd/yyyy).
--  2. Joint ventures: a contract with several suppliers has one row per
--     supplier. When every row of such a contract shows the same amount, the
--     amount is the contract total repeated, so it must be counted once.
--     amount_usd_for_totals holds the amount to use when summing money:
--     the full amount on the first row and 0 on the repeats. When the amounts
--     differ, each row is that supplier's own share and is kept.
--  3. Standardise supplier names with the same rule as TED winners, so the two
--     sources can be compared.
--  4. Flag implausible amounts (below 100 USD) instead of deleting them.

COPY (
    WITH typed AS (                                                         -- rule 1
        SELECT
            wb_contract_number                                         AS contract_id,
            TRY_CAST(fiscal_year AS INTEGER)                           AS fiscal_year,
            TRY_STRPTIME(contract_signing_date, '%m/%d/%Y')::DATE      AS signing_date,
            TRY_CAST(contract_signed_calendar_year AS INTEGER)         AS signing_year,
            region,
            borrower_country_economy                                   AS borrower_country,
            borrower_country_economy_code                              AS borrower_country_code,
            project_id,
            project_name,
            project_global_practice                                    AS global_practice,
            procurement_category,
            procurement_method,
            contract_description,
            supplier_id,
            supplier                                                   AS supplier_name,
            standardize_name(supplier)                                 AS supplier_name_std,   -- rule 3
            supplier_country_economy                                   AS supplier_country,
            supplier_country_economy_code                              AS supplier_country_code,
            TRY_CAST(supplier_contract_amount_usd AS DOUBLE)           AS amount_usd,
            review_type,
            source_file
        FROM {raw_table}
    ),

    with_contract_context AS (
        SELECT
            *,
            COUNT(*) OVER (PARTITION BY contract_id)                    AS suppliers_on_contract,
            COUNT(DISTINCT amount_usd) OVER (PARTITION BY contract_id)  AS distinct_amounts_on_contract,
            ROW_NUMBER() OVER (PARTITION BY contract_id ORDER BY supplier_id) AS supplier_row_number
        FROM typed
    )

    SELECT
        * EXCLUDE (distinct_amounts_on_contract, supplier_row_number),
        CASE                                                                -- rule 2
            WHEN suppliers_on_contract = 1 THEN amount_usd
            WHEN distinct_amounts_on_contract > 1 THEN amount_usd
            WHEN supplier_row_number = 1 THEN amount_usd
            ELSE 0
        END AS amount_usd_for_totals,
        CASE                                                                -- rule 4
            WHEN amount_usd IS NULL THEN 'missing'
            WHEN amount_usd < 100 THEN 'too_low'
            ELSE 'plausible'
        END AS amount_quality
    FROM with_contract_context
) TO {output_path} (FORMAT parquet, COMPRESSION zstd);

CREATE OR REPLACE VIEW {clean_view} AS
SELECT * FROM read_parquet({output_path});
