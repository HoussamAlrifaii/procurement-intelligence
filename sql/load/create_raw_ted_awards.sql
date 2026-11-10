-- Expose the yearly TED Parquet files as one raw view.
-- A view stores no data: queries read the compressed Parquet files directly,
-- so the data exists once on disk instead of being copied into the database.
-- union_by_name matches columns by name, so a column added or dropped in a
-- given year becomes NULL for the other years instead of breaking the load.
CREATE OR REPLACE VIEW {table_name} AS
SELECT *
FROM read_parquet({parquet_paths}, union_by_name = true);
