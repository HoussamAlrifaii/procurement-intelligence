-- Most frequent values of a low-variety column (codes and categories).
SELECT
    {column} AS value,
    COUNT(*) AS row_count
FROM {table_name}
GROUP BY {column}
ORDER BY row_count DESC
LIMIT {limit};
