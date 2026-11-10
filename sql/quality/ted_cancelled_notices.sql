-- severity: info
-- rule: Rows from notices marked as cancelled.
SELECT COUNT(*) AS failing_rows
FROM {ted_table}
WHERE cancelled = '1';
