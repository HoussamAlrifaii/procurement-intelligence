-- dim_date: one row per calendar day covering both sources (2018-12-01 to 2022-12-31).
-- date_key is the date written as a number (2021-01-20 -> 20210120): compact,
-- readable, and sortable. Power BI uses this table for every time filter.
COPY (
    SELECT
        CAST(STRFTIME(day, '%Y%m%d') AS INTEGER)  AS date_key,
        CAST(day AS DATE)                          AS date,
        YEAR(day)                                  AS year,
        QUARTER(day)                               AS quarter,
        MONTH(day)                                 AS month,
        STRFTIME(day, '%B')                        AS month_name,
        STRFTIME(day, '%Y-%m')                     AS year_month
    FROM GENERATE_SERIES(DATE '2018-12-01', DATE '2022-12-31', INTERVAL 1 DAY) AS days(day)
) TO {output_path} (FORMAT parquet);

CREATE OR REPLACE VIEW dim_date AS SELECT * FROM read_parquet({output_path});
