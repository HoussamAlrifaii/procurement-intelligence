-- One row describing the market: size, prices, competition and SME access.
-- Prices use plausible, non-framework values only (framework values are ceilings).
SELECT
    COUNT(*)                                   AS awards,
    COUNT(DISTINCT notice_id)                  AS tenders,
    COUNT(DISTINCT buyer_key)                  AS buyers,
    COUNT(DISTINCT winner_name_std)            AS winners,
    QUANTILE_CONT(award_value_eur, 0.5)  FILTER (WHERE award_value_quality = 'plausible' AND NOT COALESCE(is_framework_agreement, FALSE)) AS median_value,
    QUANTILE_CONT(award_value_eur, 0.1)  FILTER (WHERE award_value_quality = 'plausible' AND NOT COALESCE(is_framework_agreement, FALSE)) AS p10_value,
    QUANTILE_CONT(award_value_eur, 0.9)  FILTER (WHERE award_value_quality = 'plausible' AND NOT COALESCE(is_framework_agreement, FALSE)) AS p90_value,
    AVG(is_single_bid) FILTER (WHERE is_competitive_procedure) AS single_bid_rate,
    AVG(CAST(winner_is_sme AS INTEGER))        AS sme_win_share
FROM matching_awards
