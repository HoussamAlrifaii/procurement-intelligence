-- Completeness and variety of one column in a raw table.
-- A value counts as filled when it is neither NULL nor blank text.
SELECT
    {column_label} AS column_name,
    COUNT(*) AS total_rows,
    AVG(CASE WHEN {column} IS NULL OR TRIM({column}) = '' THEN 0.0 ELSE 1.0 END) AS filled_share,
    COUNT(DISTINCT {column}) AS distinct_values
FROM {table_name};
