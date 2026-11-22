-- Awards matching a company's market, shared by the three market queries.
--
-- Values chosen by the assistant (sectors, country, value range) are passed as
-- bound parameters ($cpv_groups, $country, $min_value, $max_value), never pasted
-- into the SQL text, so model output cannot change the query.
CREATE OR REPLACE TEMP TABLE matching_awards AS
SELECT
    ted.*,
    fact.buyer_key
FROM ted_awards AS ted
JOIN fact_award AS fact USING (award_id)
WHERE ted.award_status = 'awarded'
  AND YEAR(ted.publication_date) BETWEEN {first_year} AND {last_year}
  AND list_contains($cpv_groups, LEFT(ted.cpv_code, 3))
  AND ($country IS NULL OR ted.buyer_country = $country)
  AND ($min_value IS NULL OR ted.award_value_eur >= $min_value)
  AND ($max_value IS NULL OR ted.award_value_eur <= $max_value)
