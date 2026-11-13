-- dim_sector: one row per CPV division (two-digit sector code), e.g. 45 = Construction work.
COPY (
    SELECT
        CAST(cpv_division AS INTEGER) AS sector_key,
        cpv_division                  AS cpv_division,
        cpv_division_name             AS sector_name
    FROM read_csv({cpv_reference_path}, all_varchar = true)
) TO {output_path} (FORMAT parquet);

CREATE OR REPLACE VIEW dim_sector AS SELECT * FROM read_parquet({output_path});
