-- severity: info
-- rule: Rows without a number of offers (they cannot be used as ML training labels).
SELECT COUNT(*) AS failing_rows
FROM {ted_table}
WHERE number_offers IS NULL OR TRIM(number_offers) = '';
