-- Awards matching a company's market, shared by the three market queries.
--
-- Values chosen by the assistant (sectors, country, value range) are passed as
-- bound parameters ($cpv_codes, $country, $min_value, $max_value), never pasted
-- into the SQL text, so model output cannot change the query. A sector is a CPV
-- code prefix of 2 to 5 digits: a division (51), group (453), class (4531) or
-- category (45314); more digits mean a more specific market.
CREATE OR REPLACE TEMP TABLE matching_awards AS
SELECT
    ted.*,
    fact.buyer_key
FROM ted_awards AS ted
JOIN fact_award AS fact USING (award_id)
WHERE ted.award_status = 'awarded'
  AND YEAR(ted.publication_date) BETWEEN {first_year} AND {last_year}
  AND list_has_any(
        [LEFT(ted.cpv_code, 2), LEFT(ted.cpv_code, 3), LEFT(ted.cpv_code, 4), LEFT(ted.cpv_code, 5)],
        $cpv_codes)
  AND ($country IS NULL OR ted.buyer_country = $country)
  AND ($min_value IS NULL OR ted.award_value_eur >= $min_value)
  AND ($max_value IS NULL OR ted.award_value_eur <= $max_value)
