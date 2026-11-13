-- Q1. How does the single-bid rate change year by year in each country?
-- Scope: competitive procedures, awards with a known number of offers.
-- Technique: GROUP BY, then LAG() to compare each year with the previous one.
WITH yearly AS (
    SELECT
        buyer.buyer_country_name    AS country,
        dates.year,
        COUNT(*)                    AS labelled_awards,
        AVG(fact.is_single_bid)     AS single_bid_rate
    FROM fact_award AS fact
    JOIN dim_buyer     AS buyer     ON fact.buyer_key = buyer.buyer_key
    JOIN dim_date      AS dates     ON fact.date_key = dates.date_key
    JOIN dim_procedure AS procedure ON fact.procedure_key = procedure.procedure_key
    WHERE fact.is_single_bid IS NOT NULL
      AND procedure.is_competitive
      AND dates.year BETWEEN 2019 AND 2022      -- a few notices dispatched in Dec 2018 are excluded
    GROUP BY buyer.buyer_country_name, dates.year
)
SELECT
    country,
    year,
    labelled_awards,
    single_bid_rate,
    single_bid_rate - LAG(single_bid_rate) OVER (PARTITION BY country ORDER BY year)
        AS change_vs_previous_year
FROM yearly
ORDER BY country, year;
