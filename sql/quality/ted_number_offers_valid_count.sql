-- severity: warning
-- rule: Where the number of offers is filled in, it is a whole number of at least 0.
SELECT COUNT(*) AS failing_rows
FROM {ted_table}
WHERE number_offers IS NOT NULL
  AND TRIM(number_offers) <> ''
  AND (TRY_CAST(number_offers AS INTEGER) IS NULL OR TRY_CAST(number_offers AS INTEGER) < 0);
