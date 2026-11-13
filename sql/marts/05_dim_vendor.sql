-- dim_vendor: one row per company, identified by standardised name + country,
-- shared by BOTH fact tables (TED winners and World Bank suppliers).
--
-- Because the two sources use the same key, a company that won in both markets
-- is one row here, with in_ted and in_world_bank both TRUE.
COPY (
    WITH ted_vendors AS (
        SELECT
            winner_name_std AS vendor_name_std,
            winner_country  AS vendor_country,
            MODE(winner_name)   AS vendor_name,
            MODE(winner_is_sme) AS is_sme,
            COUNT(*)            AS ted_awards
        FROM ted_awards
        WHERE winner_name_std IS NOT NULL
        GROUP BY winner_name_std, winner_country
    ),
    world_bank_vendors AS (
        SELECT
            supplier_name_std     AS vendor_name_std,
            supplier_country_code AS vendor_country,
            MODE(supplier_name)   AS vendor_name,
            COUNT(DISTINCT contract_id) AS world_bank_contracts
        FROM world_bank_awards
        WHERE supplier_name_std IS NOT NULL
        GROUP BY supplier_name_std, supplier_country_code
    ),
    all_vendors AS (
        SELECT
            COALESCE(ted.vendor_name_std, wb.vendor_name_std) AS vendor_name_std,
            COALESCE(ted.vendor_country, wb.vendor_country)   AS vendor_country,
            COALESCE(ted.vendor_name, wb.vendor_name)         AS vendor_name,
            ted.is_sme,
            COALESCE(ted.ted_awards, 0)            AS ted_awards,
            COALESCE(wb.world_bank_contracts, 0)   AS world_bank_contracts
        FROM ted_vendors AS ted
        FULL OUTER JOIN world_bank_vendors AS wb
            ON  ted.vendor_name_std = wb.vendor_name_std
            AND ted.vendor_country IS NOT DISTINCT FROM wb.vendor_country
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY vendor_country, vendor_name_std) AS vendor_key,
        vendor_name,
        vendor_name_std,
        vendor_country,
        is_sme,
        ted_awards,
        world_bank_contracts,
        ted_awards > 0           AS in_ted,
        world_bank_contracts > 0 AS in_world_bank
    FROM all_vendors
) TO {output_path} (FORMAT parquet);

CREATE OR REPLACE VIEW dim_vendor AS SELECT * FROM read_parquet({output_path});
