-- Feature table for the single-bid risk model.
--
-- One row per awarded contract in a competitive procedure with a known number of
-- offers (the same population as the dashboard's competitive single-bid rate).
--
-- Every feature must be known BEFORE the tender is published. The number of
-- offers, the award value, the winner and the award date are only known after
-- bidding closes, so they are never used as features (the number of offers only
-- defines the label, is_single_bid).
--
-- Buyer history: for each award, the buyer's earlier labelled awards, counting only
-- award notices published at least {history_lag_days} days before this one. An award
-- notice appears months after the tender was first advertised, so the lag keeps
-- outcomes that were not yet public at advertising time out of the history.
COPY (
    WITH labelled AS (
        SELECT
            ted.award_id,
            ted.notice_id,
            ted.publication_date,
            YEAR(ted.publication_date)  AS publication_year,
            MONTH(ted.publication_date) AS publication_month,
            fact.buyer_key,
            ted.buyer_country,
            COALESCE(ted.buyer_type, 'Not reported')          AS buyer_type,
            COALESCE(ted.buyer_main_activity, 'Not reported') AS buyer_main_activity,
            ted.contract_type,
            ted.procedure_type,
            COALESCE(ted.award_criterion, 'Not reported')     AS award_criterion,
            COALESCE(ted.cpv_division, 'Not reported')        AS cpv_division,
            CAST(COALESCE(ted.is_framework_agreement, FALSE) AS INTEGER)  AS is_framework_agreement,
            CAST(COALESCE(ted.is_eu_funded, FALSE) AS INTEGER)            AS is_eu_funded,
            CAST(COALESCE(ted.is_gpa_covered, FALSE) AS INTEGER)          AS is_gpa_covered,
            CAST(COALESCE(ted.used_electronic_auction, FALSE) AS INTEGER) AS used_electronic_auction,
            ted.lots_in_notice,
            -- Same plausibility range as award values: below EUR 100 or from EUR 1bn
            -- the estimate is almost always a data-entry error, so it is treated as missing.
            CASE
                WHEN ted.estimated_value_eur >= 100 AND ted.estimated_value_eur < 1e9
                THEN LN(ted.estimated_value_eur)
            END AS log_estimated_value,
            ted.is_single_bid
        FROM ted_awards AS ted
        JOIN fact_award AS fact USING (award_id)
        WHERE ted.is_competitive_procedure
          AND ted.is_single_bid IS NOT NULL
    ),

    -- Rate the buyer history is shrunk towards, from the training years only.
    training_rate AS (
        SELECT AVG(is_single_bid) AS rate
        FROM labelled
        WHERE publication_year <= {train_end_year}
    ),

    buyer_days AS (
        SELECT
            buyer_key,
            publication_date,
            COUNT(*)           AS awards,
            SUM(is_single_bid) AS single_bids
        FROM labelled
        GROUP BY buyer_key, publication_date
    ),

    buyer_history AS (
        SELECT
            buyer_key,
            publication_date,
            COALESCE(SUM(awards) OVER earlier, 0)      AS prior_awards,
            COALESCE(SUM(single_bids) OVER earlier, 0) AS prior_single_bids
        FROM buyer_days
        WINDOW earlier AS (
            PARTITION BY buyer_key
            ORDER BY publication_date
            RANGE BETWEEN UNBOUNDED PRECEDING AND INTERVAL {history_lag_days} DAYS PRECEDING
        )
    )

    SELECT
        labelled.* EXCLUDE (is_single_bid),
        buyer_history.prior_awards AS buyer_prior_awards,
        -- Smoothed rate: a buyer with 2 earlier awards, both single-bid, is not
        -- treated as a "100% buyer". With few awards the value stays close to the
        -- training rate; with many it approaches the buyer's own rate.
        (buyer_history.prior_single_bids + {smoothing_awards} * training_rate.rate)
            / (buyer_history.prior_awards + {smoothing_awards}) AS buyer_prior_single_bid_rate,
        labelled.is_single_bid
    FROM labelled
    JOIN buyer_history USING (buyer_key, publication_date)
    CROSS JOIN training_rate
) TO {output_path} (FORMAT parquet);
