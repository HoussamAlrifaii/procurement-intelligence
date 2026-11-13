-- Q7. Which companies win both EU tenders and World Bank contracts, and how much?
-- Technique: one dimension (dim_vendor) shared by two fact tables. Each fact is
-- aggregated per vendor first, then joined, which avoids multiplying rows.
-- Framework agreements are excluded from value sums: their published value is a
-- ceiling for future orders, not actual spending (they are 18% of priced awards
-- but about half of all published value).
WITH eu AS (
    SELECT
        vendor_key,
        COUNT(*) AS eu_awards,
        SUM(CASE WHEN NOT COALESCE(is_framework_agreement, FALSE)
                 THEN award_value_eur_plausible END) AS eu_value_eur
    FROM fact_award
    WHERE is_awarded = 1
    GROUP BY vendor_key
),
world_bank AS (
    SELECT vendor_key, COUNT(DISTINCT contract_id) AS world_bank_contracts,
           SUM(amount_usd_for_totals) AS world_bank_value_usd
    FROM fact_world_bank_contract
    GROUP BY vendor_key
)
SELECT
    vendor.vendor_name,
    vendor.vendor_country,
    eu.eu_awards,
    eu.eu_value_eur,
    world_bank.world_bank_contracts,
    world_bank.world_bank_value_usd
FROM dim_vendor AS vendor
JOIN eu         ON vendor.vendor_key = eu.vendor_key
JOIN world_bank ON vendor.vendor_key = world_bank.vendor_key
WHERE vendor.in_ted AND vendor.in_world_bank
ORDER BY world_bank.world_bank_value_usd DESC;
