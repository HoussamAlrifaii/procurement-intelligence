-- Expose the World Bank Parquet file as a raw view, keeping only contracts
-- signed in the project's analysis years, so both sources cover the same period.
CREATE OR REPLACE VIEW {table_name} AS
SELECT *
FROM read_parquet({parquet_path})
WHERE TRY_CAST(contract_signed_calendar_year AS INTEGER) IN ({year_list});
