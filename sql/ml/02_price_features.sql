-- Feature table for the fair price model (expected award value).
--
-- One row per awarded contract with a plausible award value. Framework
-- agreements are excluded: their published value is a ceiling for future
-- orders, not a price.
--
-- The target is the natural log of the award value: prices range from EUR 100
-- to EUR 1bn, and on the log scale an error of 0.1 means "about 10% off" for a
-- small contract and a large one alike.
--
-- As in the single-bid model, every feature is known before the tender is
-- published, and the buyer's price history skips award notices published in
-- the last {history_lag_days} days.
COPY (
    WITH priced AS (
        SELECT
            ted.award_id,
            ted.notice_id,
            ted.publication_date,
            YEAR(ted.publication_date)  AS publication_year,
            MONTH(ted.publication_date) AS publication_month,
            fact.buyer_key,
            ted.buyer_country,
            COALESCE(ted.buyer_type, 'Not reported')          AS buyer_type,
            COALESCE(ted.buyer_main_activity, 'Not reported') AS buyer_main_activity,
            ted.contract_type,
            ted.procedure_type,
            COALESCE(ted.award_criterion, 'Not reported')     AS award_criterion,
            COALESCE(ted.cpv_division, 'Not reported')        AS cpv_division,
            -- CPV group (first 3 digits) separates e.g. medical equipment (331)
            -- from pharmaceuticals (336) inside division 33, which matters for price.
            COALESCE(LEFT(ted.cpv_code, 3), 'Not reported')   AS cpv_group,
            CAST(COALESCE(ted.is_eu_funded, FALSE) AS INTEGER)            AS is_eu_funded,
            CAST(COALESCE(ted.is_gpa_covered, FALSE) AS INTEGER)          AS is_gpa_covered,
            CAST(COALESCE(ted.used_electronic_auction, FALSE) AS INTEGER) AS used_electronic_auction,
            ted.lots_in_notice,
            CASE
                WHEN ted.estimated_value_eur >= 100 AND ted.estimated_value_eur < 1e9
                THEN LN(ted.estimated_value_eur)
            END AS log_estimated_value,
            -- Kept for evaluation only (never a feature): an estimate identical to
            -- the award value may have been filled in after the award.
            ABS(ted.estimated_value_eur - ted.award_value_eur) < 1 AS estimate_equals_award,
            LN(ted.award_value_eur) AS log_award_value
        FROM ted_awards AS ted
        JOIN fact_award AS fact USING (award_id)
        WHERE ted.award_status = 'awarded'
          AND ted.award_value_quality = 'plausible'
          AND NOT COALESCE(ted.is_framework_agreement, FALSE)
    ),

    buyer_days AS (
        SELECT
            buyer_key,
            publication_date,
            COUNT(*)             AS awards,
            SUM(log_award_value) AS sum_log_value
        FROM priced
        GROUP BY buyer_key, publication_date
    ),

    buyer_history AS (
        SELECT
            buyer_key,
            publication_date,
            COALESCE(SUM(awards) OVER earlier, 0) AS prior_awards,
            SUM(sum_log_value) OVER earlier       AS prior_sum_log_value
        FROM buyer_days
        WINDOW earlier AS (
            PARTITION BY buyer_key
            ORDER BY publication_date
            RANGE BETWEEN UNBOUNDED PRECEDING AND INTERVAL {history_lag_days} DAYS PRECEDING
        )
    )

    SELECT
        priced.* EXCLUDE (estimate_equals_award, log_award_value),
        buyer_history.prior_awards AS buyer_prior_priced_awards,
        -- Mean log value = log of the geometric mean: the buyer's typical contract size.
        -- Missing when the buyer has no earlier priced award; LightGBM handles that.
        buyer_history.prior_sum_log_value / NULLIF(buyer_history.prior_awards, 0) AS buyer_prior_mean_log_value,
        priced.estimate_equals_award,
        priced.log_award_value
    FROM priced
    JOIN buyer_history USING (buyer_key, publication_date)
) TO {output_path} (FORMAT parquet);
