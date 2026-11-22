-- Companies that won the most contracts in this market (the likely competitors).
SELECT
    MODE(winner_name)                          AS company,
    winner_country                             AS country,
    COUNT(*)                                   AS awards,
    BOOL_OR(winner_is_sme)                     AS is_sme
FROM matching_awards
WHERE winner_name_std IS NOT NULL
GROUP BY winner_name_std, winner_country
ORDER BY awards DESC
LIMIT 5
