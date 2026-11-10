-- severity: critical
-- rule: Every TED row has a notice identifier.
SELECT COUNT(*) AS failing_rows
FROM {ted_table}
WHERE id_notice_can IS NULL OR TRIM(id_notice_can) = '';
