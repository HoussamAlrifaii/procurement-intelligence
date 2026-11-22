-- Buyers that awarded the most contracts in this market. Buyers are grouped by
-- their standardised key, so different spellings of one buyer count together.
SELECT
    buyers.buyer_name                          AS buyer,
    buyers.buyer_country                       AS country,
    COUNT(*)                                   AS awards,
    QUANTILE_CONT(matching_awards.award_value_eur, 0.5)
        FILTER (WHERE matching_awards.award_value_quality = 'plausible') AS median_value
FROM matching_awards
JOIN dim_buyer AS buyers USING (buyer_key)
GROUP BY buyers.buyer_key, buyers.buyer_name, buyers.buyer_country
ORDER BY awards DESC
LIMIT 5
