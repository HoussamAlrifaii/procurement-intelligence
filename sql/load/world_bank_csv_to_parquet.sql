-- Convert the World Bank contract awards CSV to Parquet.
-- Columns are read as text and header names are normalised to snake_case,
-- e.g. "Supplier Contract Amount (USD)" -> supplier_contract_amount_usd.
COPY (
    SELECT
        *,
        {source_file} AS source_file
    FROM read_csv(
        {csv_path},
        header = true,
        all_varchar = true,
        normalize_names = true
    )
) TO {parquet_path} (FORMAT parquet, COMPRESSION zstd);
