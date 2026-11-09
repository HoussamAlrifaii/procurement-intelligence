-- severity: warning
-- rule: Every World Bank contract amount is a number of at least 0.
SELECT COUNT(*) AS failing_rows
FROM {world_bank_table}
WHERE TRY_CAST(supplier_contract_amount_usd AS DOUBLE) IS NULL
   OR TRY_CAST(supplier_contract_amount_usd AS DOUBLE) < 0;
