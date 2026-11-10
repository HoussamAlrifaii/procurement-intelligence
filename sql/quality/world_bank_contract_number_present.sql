-- severity: critical
-- rule: Every World Bank row has a contract number.
SELECT COUNT(*) AS failing_rows
FROM {world_bank_table}
WHERE wb_contract_number IS NULL OR TRIM(wb_contract_number) = '';
