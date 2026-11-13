-- Q3. How concentrated is each buyer's spending across vendors?
-- Scope: awarded contracts with a plausible value and a known winner; buyers
-- with at least 50 such awards.
-- Technique: CTEs + window functions (SUM() OVER) to compute each vendor's
-- share of a buyer's spending, then the Herfindahl-Hirschman Index (HHI):
--     HHI = sum over vendors of (share x 100)^2
-- It ranges from near 0 (spending spread over many vendors) to 10,000 (one
-- vendor gets everything). Competition authorities have long used 1,500 and
-- 2,500 as the bands for moderate and high concentration.
-- Framework agreements are excluded from value sums: their published value is a
-- ceiling for future orders, not actual spending (they are 18% of priced awards
-- but about half of all published value).
WITH buyer_vendor AS (
    SELECT
        buyer_key,
        vendor_key,
        COUNT(*)                        AS awards,
        SUM(award_value_eur_plausible)  AS value_eur
    FROM fact_award
    WHERE is_awarded = 1
      AND vendor_key IS NOT NULL
      AND award_value_eur_plausible IS NOT NULL
      AND NOT COALESCE(is_framework_agreement, FALSE)
    GROUP BY buyer_key, vendor_key
),
shares AS (
    SELECT
        buyer_key,
        awards,
        value_eur,
        value_eur / SUM(value_eur) OVER (PARTITION BY buyer_key) AS value_share
    FROM buyer_vendor
)
SELECT
    buyer.buyer_name,
    buyer.buyer_country_name             AS country,
    SUM(shares.awards)                   AS awards,
    COUNT(*)                             AS vendors,
    SUM(shares.value_eur)                AS total_value_eur,
    MAX(shares.value_share)              AS top_vendor_share,
    SUM(POWER(shares.value_share * 100, 2)) AS hhi,
    CASE
        WHEN SUM(POWER(shares.value_share * 100, 2)) >= 2500 THEN 'high'
        WHEN SUM(POWER(shares.value_share * 100, 2)) >= 1500 THEN 'moderate'
        ELSE 'low'
    END                                  AS concentration
FROM shares
JOIN dim_buyer AS buyer ON shares.buyer_key = buyer.buyer_key
GROUP BY buyer.buyer_key, buyer.buyer_name, buyer.buyer_country_name
HAVING SUM(shares.awards) >= 50
ORDER BY hhi DESC;
