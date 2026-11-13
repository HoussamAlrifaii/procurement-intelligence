-- dim_procedure: one row per procedure code found in the data, with its label and
-- whether it includes a public call for competition. Key 0 = procedure not reported.
COPY (
    WITH procedures AS (
        SELECT DISTINCT procedure_code, procedure_type, is_competitive_procedure
        FROM ted_awards
        WHERE procedure_code IS NOT NULL
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY procedure_code) AS procedure_key,
        procedure_code,
        procedure_type,
        is_competitive_procedure                    AS is_competitive
    FROM procedures
    UNION ALL
    SELECT 0, NULL, 'Not reported', NULL
) TO {output_path} (FORMAT parquet);

CREATE OR REPLACE VIEW dim_procedure AS SELECT * FROM read_parquet({output_path});
