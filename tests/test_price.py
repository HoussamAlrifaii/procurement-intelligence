"""Tests for the fair price model: feature table, baseline, ranges and flags."""
import duckdb
import numpy as np
import pandas as pd
import pytest

from procurement import config
from procurement.evaluate import interval_metrics, regression_metrics
from procurement.features import POST_PUBLICATION_COLUMNS
from procurement.price_features import (EVALUATION_COLUMNS, FEATURES, build_price_feature_table,
                                        load_price_features)
from procurement.price_train import PeerMedianBaseline, flag_unusual_prices, predict_range

AWARDS = [
    # award_id, publication_date, award_value_eur, quality, framework, estimated_value_eur
    (1, "2020-01-01", 100_000.0, "plausible", False, 100_000.0),   # estimate equals award
    (2, "2020-03-01", 10_000.0, "plausible", False, 12_000.0),
    (3, "2020-08-01", 1_000.0, "plausible", False, None),
    (4, "2020-08-01", 5_000_000.0, "plausible", True, None),       # framework ceiling: excluded
    (5, "2020-09-01", 50.0, "too_low", False, None),               # implausible value: excluded
]


@pytest.fixture(scope="module")
def features(tmp_path_factory):
    rows = []
    for award_id, publication_date, value, quality, framework, estimate in AWARDS:
        rows.append({
            "award_id": award_id, "notice_id": award_id, "publication_date": pd.Timestamp(publication_date),
            "award_status": "awarded", "award_value_eur": value, "award_value_quality": quality,
            "is_framework_agreement": framework, "estimated_value_eur": estimate,
            "buyer_country": "PL", "buyer_type": "Utilities", "buyer_main_activity": None,
            "contract_type": "Works", "procedure_type": "Open", "award_criterion": None,
            "cpv_division": "45", "cpv_code": "45233140", "is_eu_funded": True,
            "is_gpa_covered": False, "used_electronic_auction": None, "lots_in_notice": 2,
        })
    ted_awards = pd.DataFrame(rows)
    fact_award = pd.DataFrame({"award_id": ted_awards["award_id"], "buyer_key": 3})

    output_path = tmp_path_factory.mktemp("price") / "price_features.parquet"
    with duckdb.connect() as connection:
        connection.register("ted_awards", ted_awards)
        connection.register("fact_award", fact_award)
        build_price_feature_table(connection, output_path)
    return load_price_features(output_path).set_index("award_id")


def test_features_exclude_post_publication_and_evaluation_columns():
    assert not set(FEATURES) & set(POST_PUBLICATION_COLUMNS)
    assert not set(FEATURES) & set(EVALUATION_COLUMNS)
    assert "log_award_value" not in FEATURES


def test_only_plausible_non_framework_awards_are_kept(features):
    assert sorted(features.index) == [1, 2, 3]


def test_target_is_log_award_value(features):
    assert features.loc[2, "log_award_value"] == pytest.approx(np.log(10_000))


def test_cpv_group_is_first_three_digits(features):
    assert features.loc[1, "cpv_group"] == "452"


def test_estimate_equal_to_award_is_marked_for_evaluation(features):
    assert bool(features.loc[1, "estimate_equals_award"]) is True
    assert bool(features.loc[2, "estimate_equals_award"]) is False


def test_buyer_price_history_respects_the_lag(features):
    assert config.BUYER_HISTORY_LAG_DAYS == 180
    assert features.loc[2, "buyer_prior_priced_awards"] == 0
    assert pd.isna(features.loc[2, "buyer_prior_mean_log_value"])
    # Award 3: only award 1 (213 days earlier) counts.
    assert features.loc[3, "buyer_prior_priced_awards"] == 1
    assert features.loc[3, "buyer_prior_mean_log_value"] == pytest.approx(np.log(100_000))


def test_peer_baseline_falls_back_to_broader_groups():
    train = pd.DataFrame({
        "cpv_division": ["45", "45", "45", "33"],
        "buyer_country": ["PL", "PL", "DE", "PL"],
        "contract_type": ["Works"] * 4,
        "log_award_value": [10.0, 12.0, 14.0, 8.0],
    })
    baseline = PeerMedianBaseline().fit(train)
    new = pd.DataFrame({
        "cpv_division": ["45", "45", "99"],
        "buyer_country": ["PL", "FR", "PL"],
        "contract_type": ["Works"] * 3,
    })
    prediction = baseline.predict(new)
    assert prediction[0] == pytest.approx(11.0)   # exact peer group: PL works in 45
    assert prediction[1] == pytest.approx(12.0)   # no FR group: all works in 45
    assert prediction[2] == pytest.approx(11.0)   # unknown sector: overall median


class FixedModel:
    def __init__(self, value):
        self.value = value

    def predict(self, frame):
        return np.full(len(frame), self.value)


def test_predicted_range_is_sorted_when_quantile_models_cross():
    frame = pd.DataFrame({name: [0.0] for name in FEATURES})
    models = {0.1: FixedModel(12.0), 0.5: FixedModel(10.0), 0.9: FixedModel(11.0)}
    predicted = predict_range(models, frame)
    assert predicted.iloc[0].tolist() == [10.0, 11.0, 12.0]


def test_unusual_prices_are_flagged_outside_the_widened_range():
    predicted = pd.DataFrame({"log_p10": [np.log(100.0)] * 3, "log_p90": [np.log(200.0)] * 3})
    actual = np.log([150.0, 450.0, 40.0])
    assert flag_unusual_prices(actual, predicted, factor=2.0).tolist() == ["expected", "high", "low"]


def test_regression_and_interval_metrics():
    actual = np.log([100.0, 1000.0])
    predicted = np.log([110.0, 1900.0])
    metrics = regression_metrics(actual, predicted)
    assert metrics["within_25pct"] == 0.5
    assert metrics["within_factor_2"] == 1.0
    coverage = interval_metrics(actual, np.log([90.0, 1200.0]), np.log([150.0, 3000.0]))
    assert coverage["coverage"] == 0.5
