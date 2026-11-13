-- dim_buyer: one row per buyer, identified by standardised name + country.
--
-- The same buyer is spelled in many ways (153,502 raw spellings -> 95,024 buyers).
-- For display, each buyer keeps its most frequent raw spelling; its buyer type is
-- also the most frequent one (a buyer can report different types across notices).
-- Joint purchases list several buyers joined with '---'; like the standardised
-- name, the display name keeps the first (lead) buyer.
-- buyer_key is a surrogate key: a small integer created here, used to join the fact table.
COPY (
    WITH buyer_rows AS (
        SELECT
            standardize_name(buyer_name) AS buyer_name_std,
            buyer_country,
            TRIM(SPLIT_PART(buyer_name, '---', 1)) AS buyer_name,
            buyer_type
        FROM ted_awards
        WHERE standardize_name(buyer_name) IS NOT NULL
    ),
    buyers AS (
        SELECT
            buyer_name_std,
            buyer_country,
            MODE(buyer_name) AS buyer_name,
            MODE(buyer_type) AS buyer_type,
            COUNT(*)         AS award_records
        FROM buyer_rows
        GROUP BY buyer_name_std, buyer_country
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY buyers.buyer_country, buyers.buyer_name_std) AS buyer_key,
        buyers.buyer_name,
        buyers.buyer_name_std,
        buyers.buyer_country,
        countries.country_name AS buyer_country_name,
        buyers.buyer_type,
        buyers.award_records
    FROM buyers
    LEFT JOIN read_csv({countries_path}, all_varchar = true) AS countries
        ON buyers.buyer_country = countries.country_code
) TO {output_path} (FORMAT parquet);

CREATE OR REPLACE VIEW dim_buyer AS SELECT * FROM read_parquet({output_path});
