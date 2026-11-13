-- Q6. How many awards are priced far above similar contracts?
-- "Similar" = same sector, contract type and buyer country (groups of 30+ awards).
-- Contract values span several orders of magnitude, so the comparison is made on
-- a log scale, with the standard Tukey outlier rule:
--     anomaly if log10(value) > Q3 + 1.5 x IQR   (IQR = Q3 - Q1 of the group)
-- Technique: QUANTILE_CONT() OVER (PARTITION BY ...) compares each row with its group.
-- A high value can be legitimate (a genuinely larger contract); it is a signal for
-- review and a candidate feature for the anomaly model in Phase 5.
-- Framework agreements are excluded from value sums: their published value is a
-- ceiling for future orders, not actual spending (they are 18% of priced awards
-- but about half of all published value).
WITH priced AS (
    SELECT
        fact.sector_key,
        LOG10(fact.award_value_eur_plausible)                          AS log_value,
        QUANTILE_CONT(LOG10(fact.award_value_eur_plausible), 0.25) OVER group_window AS group_q1,
        QUANTILE_CONT(LOG10(fact.award_value_eur_plausible), 0.75) OVER group_window AS group_q3,
        COUNT(*) OVER group_window                                     AS group_awards
    FROM fact_award AS fact
    JOIN dim_buyer AS buyer ON fact.buyer_key = buyer.buyer_key
    WHERE fact.is_awarded = 1
      AND fact.award_value_eur_plausible IS NOT NULL
      AND NOT COALESCE(fact.is_framework_agreement, FALSE)
    WINDOW group_window AS (PARTITION BY fact.sector_key, fact.contract_type, buyer.buyer_country)
),
flagged AS (
    SELECT
        sector_key,
        log_value > group_q3 + 1.5 * (group_q3 - group_q1) AS is_anomaly
    FROM priced
    WHERE group_awards >= 30
)
SELECT
    sector.sector_name,
    COUNT(*)                                             AS awards,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END)          AS anomalies,
    AVG(CASE WHEN is_anomaly THEN 1.0 ELSE 0.0 END)      AS anomaly_share
FROM flagged
JOIN dim_sector AS sector ON flagged.sector_key = sector.sector_key
GROUP BY sector.sector_name
ORDER BY anomaly_share DESC;
