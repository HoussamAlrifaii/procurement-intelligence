-- severity: warning
-- rule: Where the award value is filled in, it is a number of at least 0.
SELECT COUNT(*) AS failing_rows
FROM {ted_table}
WHERE award_value_euro IS NOT NULL
  AND TRIM(award_value_euro) <> ''
  AND (TRY_CAST(award_value_euro AS DOUBLE) IS NULL OR TRY_CAST(award_value_euro AS DOUBLE) < 0);
