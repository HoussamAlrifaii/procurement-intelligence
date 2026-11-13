-- Q2. Which buyers have the highest single-bid rates? (an auditor's starting list)
-- Scope: competitive procedures; buyers with at least 100 labelled awards, so
-- that a rate is not driven by a handful of contracts.
-- Technique: CTEs, HAVING, RANK() overall and within each country.
-- A high rate is a risk indicator worth a closer look, not evidence of wrongdoing.
WITH competitive_awards AS (
    SELECT fact.buyer_key, fact.is_single_bid
    FROM fact_award AS fact
    JOIN dim_procedure AS procedure ON fact.procedure_key = procedure.procedure_key
    WHERE fact.is_single_bid IS NOT NULL
      AND procedure.is_competitive
),
buyer_rates AS (
    SELECT buyer_key, COUNT(*) AS labelled_awards, AVG(is_single_bid) AS single_bid_rate
    FROM competitive_awards
    GROUP BY buyer_key
    HAVING COUNT(*) >= 100
),
country_rates AS (
    SELECT buyer.buyer_country, AVG(awards.is_single_bid) AS country_rate
    FROM competitive_awards AS awards
    JOIN dim_buyer AS buyer ON awards.buyer_key = buyer.buyer_key
    GROUP BY buyer.buyer_country
)
SELECT
    RANK() OVER (ORDER BY rates.single_bid_rate DESC, rates.labelled_awards DESC) AS overall_rank,
    RANK() OVER (PARTITION BY buyer.buyer_country
                 ORDER BY rates.single_bid_rate DESC, rates.labelled_awards DESC) AS rank_in_country,
    buyer.buyer_name,
    buyer.buyer_country_name                                    AS country,
    buyer.buyer_type,
    rates.labelled_awards,
    rates.single_bid_rate,
    countries.country_rate,
    rates.single_bid_rate - countries.country_rate              AS gap_vs_country
FROM buyer_rates AS rates
JOIN dim_buyer     AS buyer     ON rates.buyer_key = buyer.buyer_key
JOIN country_rates AS countries ON buyer.buyer_country = countries.buyer_country
ORDER BY overall_rank;
