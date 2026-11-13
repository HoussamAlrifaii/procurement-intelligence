-- Q5. Which vendors win the largest share of each sector's spending?
-- Scope: awarded contracts with a plausible value and a known winner.
-- Technique: SUM() OVER (PARTITION BY sector) for shares, ROW_NUMBER() to keep
-- the top 3 vendors per sector.
-- Framework agreements are excluded from value sums: their published value is a
-- ceiling for future orders, not actual spending (they are 18% of priced awards
-- but about half of all published value).
WITH sector_vendor AS (
    SELECT
        sector_key,
        vendor_key,
        SUM(award_value_eur_plausible) AS value_eur
    FROM fact_award
    WHERE is_awarded = 1
      AND vendor_key IS NOT NULL
      AND award_value_eur_plausible IS NOT NULL
      AND NOT COALESCE(is_framework_agreement, FALSE)
    GROUP BY sector_key, vendor_key
),
ranked AS (
    SELECT
        sector_key,
        vendor_key,
        value_eur,
        value_eur / SUM(value_eur) OVER (PARTITION BY sector_key)      AS share_of_sector,
        ROW_NUMBER() OVER (PARTITION BY sector_key ORDER BY value_eur DESC) AS vendor_rank
    FROM sector_vendor
)
SELECT
    sector.sector_name,
    ranked.vendor_rank,
    vendor.vendor_name,
    vendor.vendor_country,
    ranked.value_eur,
    ranked.share_of_sector
FROM ranked
JOIN dim_sector AS sector ON ranked.sector_key = sector.sector_key
JOIN dim_vendor AS vendor ON ranked.vendor_key = vendor.vendor_key
WHERE ranked.vendor_rank <= 3
ORDER BY sector.sector_name, ranked.vendor_rank;
