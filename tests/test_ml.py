"""Tests for the single-bid model: leakage guards, buyer history, split and metrics."""
import duckdb
import numpy as np
import pandas as pd
import pytest

from procurement import config
from procurement.evaluate import best_f1_threshold, calibration_table, lift_at_top, threshold_metrics
from procurement.features import (FEATURES, POST_PUBLICATION_COLUMNS, build_feature_table,
                                  load_features, split_by_year)

# One buyer with three labelled competitive awards, plus two rows the model must ignore.
AWARDS = [
    # award_id, publication_date, competitive, is_single_bid, estimated_value_eur
    (1, "2020-01-01", True, 1, 50_000.0),
    (2, "2020-03-01", True, 0, 50.0),          # implausible estimate -> missing
    (3, "2020-08-01", True, 1, None),
    (4, "2020-08-01", False, 1, 50_000.0),     # negotiated without competition: excluded
    (5, "2020-09-01", True, None, 50_000.0),   # number of offers unknown: excluded
]


@pytest.fixture(scope="module")
def features(tmp_path_factory):
    rows = []
    for award_id, publication_date, competitive, single_bid, estimate in AWARDS:
        rows.append({
            "award_id": award_id, "notice_id": award_id, "publication_date": pd.Timestamp(publication_date),
            "buyer_country": "PL", "buyer_type": None, "buyer_main_activity": "Health",
            "contract_type": "Supplies", "procedure_type": "Open", "award_criterion": "Lowest price",
            "cpv_division": "33", "is_framework_agreement": False, "is_eu_funded": None,
            "is_gpa_covered": True, "used_electronic_auction": False, "lots_in_notice": 1,
            "estimated_value_eur": estimate, "is_competitive_procedure": competitive,
            "is_single_bid": single_bid,
        })
    ted_awards = pd.DataFrame(rows)
    fact_award = pd.DataFrame({"award_id": ted_awards["award_id"], "buyer_key": 7})

    output_path = tmp_path_factory.mktemp("ml") / "features.parquet"
    with duckdb.connect() as connection:
        connection.register("ted_awards", ted_awards)
        connection.register("fact_award", fact_award)
        build_feature_table(connection, output_path)
    return load_features(output_path).set_index("award_id")


def test_no_post_publication_column_is_a_feature():
    leaking = set(FEATURES) & set(POST_PUBLICATION_COLUMNS)
    assert not leaking, f"features known only after bidding closes: {leaking}"


def test_only_labelled_competitive_awards_are_kept(features):
    assert sorted(features.index) == [1, 2, 3]


def test_buyer_history_only_counts_awards_published_before_the_lag(features):
    assert config.BUYER_HISTORY_LAG_DAYS == 180
    # Award 2 is 60 days after award 1: too recent to count.
    assert features.loc[2, "buyer_prior_awards"] == 0
    # Award 3: award 1 (213 days earlier) counts, award 2 (153 days earlier) does not.
    assert features.loc[3, "buyer_prior_awards"] == 1


def test_buyer_history_rate_is_shrunk_towards_the_training_rate(features):
    training_rate = 2 / 3
    smoothing = config.BUYER_HISTORY_SMOOTHING
    assert features.loc[1, "buyer_prior_single_bid_rate"] == pytest.approx(training_rate)
    expected = (1 + smoothing * training_rate) / (1 + smoothing)
    assert features.loc[3, "buyer_prior_single_bid_rate"] == pytest.approx(expected)


def test_implausible_or_missing_estimates_become_missing(features):
    assert features.loc[1, "log_estimated_value"] == pytest.approx(np.log(50_000))
    assert pd.isna(features.loc[2, "log_estimated_value"])
    assert pd.isna(features.loc[3, "log_estimated_value"])


def test_missing_flags_and_categories_are_filled(features):
    assert features.loc[1, "is_eu_funded"] == 0
    assert features.loc[1, "buyer_type"] == "Not reported"


def test_split_by_year_keeps_years_apart():
    frame = pd.DataFrame({"publication_year": [2018, 2019, 2020, 2021, 2022], "notice_id": range(5)})
    splits = split_by_year(frame)
    assert splits["train"]["publication_year"].tolist() == [2018, 2019, 2020]
    assert splits["validation"]["publication_year"].tolist() == [config.VALIDATION_YEAR]
    assert splits["test"]["publication_year"].tolist() == [config.TEST_YEAR]


def test_lift_of_a_perfect_ranking_and_of_a_random_one():
    actual = np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0] * 10)
    perfect_scores = actual.astype(float)
    assert lift_at_top(actual, perfect_scores, 0.10) == pytest.approx(10.0)
    constant_scores = np.zeros(len(actual))
    assert lift_at_top(actual, constant_scores, 1.0) == pytest.approx(1.0)


def test_calibration_table_compares_predicted_and_observed_rates():
    predicted = np.linspace(0.05, 0.95, 100)
    actual = (predicted > 0.5).astype(int)
    table = calibration_table(actual, predicted, bins=2)
    assert table["observed_rate"].tolist() == [0.0, 1.0]
    assert table["rows"].sum() == 100


def test_best_threshold_separates_perfectly_ranked_classes():
    actual = np.array([0, 0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.3, 0.7, 0.9])
    threshold = best_f1_threshold(actual, scores)
    assert threshold == pytest.approx(0.7)
    metrics = threshold_metrics(actual, scores, threshold)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["flagged_share"] == pytest.approx(0.4)
