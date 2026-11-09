-- severity: critical
-- rule: Every TED notice year is one of the requested years.
SELECT COUNT(*) AS failing_rows
FROM {ted_table}
WHERE TRY_CAST(notice_year AS INTEGER) IS NULL
   OR TRY_CAST(notice_year AS INTEGER) NOT IN ({year_list});
