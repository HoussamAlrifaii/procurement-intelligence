-- Q4. Which buyer-vendor pairs repeat single-bid wins most often?
-- Scope: competitive procedures; pairs with at least 20 single-bid awards.
-- Technique: JOINs + aggregation on a pair of keys.
-- A frequent pair can have legitimate reasons (a specialised supplier, a niche
-- market); it is a pattern to examine, not a finding of wrongdoing.
SELECT
    buyer.buyer_name,
    buyer.buyer_country_name            AS buyer_country,
    vendor.vendor_name,
    vendor.vendor_country,
    COUNT(*)                            AS labelled_awards,
    SUM(fact.is_single_bid)             AS single_bid_awards,
    AVG(fact.is_single_bid)             AS single_bid_rate
FROM fact_award AS fact
JOIN dim_buyer     AS buyer     ON fact.buyer_key = buyer.buyer_key
JOIN dim_vendor    AS vendor    ON fact.vendor_key = vendor.vendor_key
JOIN dim_procedure AS procedure ON fact.procedure_key = procedure.procedure_key
WHERE fact.is_single_bid IS NOT NULL
  AND procedure.is_competitive
GROUP BY buyer.buyer_key, buyer.buyer_name, buyer.buyer_country_name,
         vendor.vendor_key, vendor.vendor_name, vendor.vendor_country
HAVING SUM(fact.is_single_bid) >= 20
ORDER BY single_bid_awards DESC;
