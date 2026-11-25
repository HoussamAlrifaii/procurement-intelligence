"""Tests for the monthly refresh and the red-flag rules (no data or models needed)."""
import argparse

import numpy as np
import pandas as pd

from procurement import red_flags, refresh

ARGUMENTS = argparse.Namespace(skip_download=True, retrain=False)


def test_steps_run_in_order():
    calls = []
    steps = [(name, lambda arguments, name=name: calls.append(name)) for name in ["one", "two", "three"]]
    assert refresh.run_steps(ARGUMENTS, steps) == 0
    assert calls == ["one", "two", "three"]


def test_a_failed_quality_check_stops_the_refresh(caplog):
    calls = []

    def failing_pipeline(arguments):
        raise SystemExit(1)

    steps = [("pipeline", failing_pipeline), ("red flags", lambda arguments: calls.append("red flags"))]
    assert refresh.run_steps(ARGUMENTS, steps) == 1
    assert calls == []
    assert "failed: pipeline" in caplog.text


def test_an_error_stops_the_refresh_and_is_logged(caplog):
    def broken(arguments):
        raise ValueError("bundle folder missing")

    assert refresh.run_steps(ARGUMENTS, [("app bundle", broken)]) == 1
    assert "bundle folder missing" in caplog.text


def test_pipeline_receives_skip_download(monkeypatch):
    received = []
    monkeypatch.setattr(refresh.pipeline, "main", lambda argv: received.append(argv))
    refresh.run_pipeline(argparse.Namespace(skip_download=True, retrain=False))
    refresh.run_pipeline(argparse.Namespace(skip_download=False, retrain=False))
    assert received == [["--skip-download"], []]


def test_buyers_to_review_uses_rate_or_gap():
    table = pd.DataFrame({
        "buyer_name": ["high rate", "far above country", "normal"],
        "single_bid_rate": [0.85, 0.55, 0.40],
        "gap_vs_country": [0.10, 0.25, 0.05],
        "labelled_awards": [120, 300, 500],
    })
    assert red_flags.select_buyers_to_review(table)["buyer_name"].tolist() == ["high rate", "far above country"]


def test_unusual_prices_keep_one_row_per_tender_and_rank_by_excess():
    frame = pd.DataFrame({
        "notice_id": [1, 1, 2, 3],
        "log_award_value": np.log([500.0, 600.0, 1_000.0, 150.0]),
    })
    predicted = pd.DataFrame({"log_p90": np.log([100.0, 100.0, 100.0, 100.0])})
    ranked = red_flags.rank_unusual_prices(frame, predicted, factor=2.0)
    assert ranked["notice_id"].tolist() == [2, 1]           # tender 3 is within 2x of the range
    assert ranked["times_above_range"].round(1).tolist() == [10.0, 6.0]   # tender 1 keeps its worst lot


def test_top_reasons_lists_features_that_raise_risk():
    contributions = pd.Series({"buyer_country": 0.9, "lots_in_notice": -0.4, "cpv_division": 0.3})
    assert red_flags.top_reasons(contributions) == "Country, Sector (CPV division)"


def test_newly_flagged_buyers():
    assert red_flags.compare_with_previous(None, {"flagged_buyers": ["A"]}) is None
    previous = {"flagged_buyers": ["A", "B"]}
    assert red_flags.compare_with_previous(previous, {"flagged_buyers": ["B", "C"]}) == ["C"]
