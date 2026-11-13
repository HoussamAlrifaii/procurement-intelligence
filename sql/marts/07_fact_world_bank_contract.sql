-- fact_world_bank_contract: one row per supplier on a World Bank contract.
-- It shares dim_vendor and dim_date with fact_award (a "galaxy" schema: two fact
-- tables connected through common dimensions).
COPY (
    SELECT
        contracts.contract_id,
        CAST(STRFTIME(contracts.signing_date, '%Y%m%d') AS INTEGER) AS date_key,
        vendor.vendor_key,
        contracts.region,
        contracts.borrower_country,
        contracts.procurement_category,
        contracts.procurement_method,
        contracts.suppliers_on_contract,
        contracts.amount_usd,
        contracts.amount_usd_for_totals,
        contracts.amount_quality
    FROM world_bank_awards AS contracts
    LEFT JOIN dim_vendor AS vendor
        ON  contracts.supplier_name_std = vendor.vendor_name_std
        AND contracts.supplier_country_code IS NOT DISTINCT FROM vendor.vendor_country
) TO {output_path} (FORMAT parquet, COMPRESSION zstd);

CREATE OR REPLACE VIEW fact_world_bank_contract AS SELECT * FROM read_parquet({output_path});
