-- fact_award: one row per TED contract award record (awarded or not), with a key
-- to each dimension and the measures dashboards aggregate.
--
-- Keys are looked up by joining the clean table to each dimension on its natural
-- key (e.g. standardised buyer name + country). LEFT JOINs keep every award even
-- when a dimension has no match (e.g. no winner), so no row is lost: the fact
-- table must have exactly as many rows as ted_awards.
COPY (
    SELECT
        awards.award_id,
        awards.notice_id,
        CAST(STRFTIME(awards.publication_date, '%Y%m%d') AS INTEGER) AS date_key,
        buyer.buyer_key,
        vendor.vendor_key,
        CAST(awards.cpv_division AS INTEGER)                         AS sector_key,
        COALESCE(procedure.procedure_key, 0)                         AS procedure_key,

        -- descriptive attributes kept on the fact (few values, no separate table needed)
        awards.contract_type,
        awards.award_criterion,
        awards.award_status,
        awards.is_framework_agreement,
        awards.is_eu_funded,
        awards.winner_count,

        -- measures
        CASE WHEN awards.award_status = 'awarded' THEN 1 ELSE 0 END  AS is_awarded,
        awards.number_offers,
        awards.is_single_bid,
        awards.award_value_eur,
        awards.award_value_quality,
        CASE WHEN awards.award_value_quality = 'plausible'
             THEN awards.award_value_eur END                         AS award_value_eur_plausible
    FROM ted_awards AS awards
    LEFT JOIN dim_buyer AS buyer
        ON  standardize_name(awards.buyer_name) = buyer.buyer_name_std
        AND awards.buyer_country = buyer.buyer_country
    LEFT JOIN dim_vendor AS vendor
        ON  awards.winner_name_std = vendor.vendor_name_std
        AND awards.winner_country IS NOT DISTINCT FROM vendor.vendor_country
    LEFT JOIN dim_procedure AS procedure
        ON  awards.procedure_code = procedure.procedure_code
) TO {output_path} (FORMAT parquet, COMPRESSION zstd);

CREATE OR REPLACE VIEW fact_award AS SELECT * FROM read_parquet({output_path});
