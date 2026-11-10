-- Convert one year of TED contract award notices from CSV to Parquet.
--
-- Every column is read as text (all_varchar). The raw layer keeps values
-- exactly as published; typing and cleaning happen in a later, documented step.
-- normalize_names converts headers to lower snake_case (ID_NOTICE_CAN ->
-- id_notice_can). YEAR is a reserved word, which DuckDB renames to _year,
-- so it is renamed explicitly to notice_year.
COPY (
    SELECT
        * RENAME (_year AS notice_year),
        {source_file} AS source_file
    FROM read_csv(
        {csv_path},
        header = true,
        all_varchar = true,
        normalize_names = true
    )
) TO {parquet_path} (FORMAT parquet, COMPRESSION zstd);
