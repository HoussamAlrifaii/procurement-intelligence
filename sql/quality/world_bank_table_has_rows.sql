-- severity: critical
-- rule: The raw World Bank table contains at least one row.
SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END AS failing_rows
FROM {world_bank_table};
