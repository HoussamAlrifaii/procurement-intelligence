"""Test how the buyer-history gap changes the single-bid model.

The award notice (our publication date) appears months after a tender is
advertised, when the prediction is really made. The buyer-history features
therefore skip the buyer's most recent awards. This experiment rebuilds the
features with different gaps and compares LightGBM on the validation year:

  1 day    - every award notice published before this one (no gap)
  90 days  - about three months
  180 days - the project setting
  365 days - one year

A clearly higher score with a short gap means recent outcomes carry information
that would not be public on the advertising day, i.e. leakage the gap removes.
Only the validation year is used; the test year stays untouched.

Usage (after the star schema exists; takes about 10 minutes):
    python -m procurement.lag_experiment
"""
import json

import duckdb

from procurement import config
from procurement.evaluate import classification_metrics
from procurement.features import FEATURES, TARGET, build_feature_table, load_features, split_by_year
from procurement.train import train_lightgbm

LAGS_TO_TEST = [1, 90, 180, 365]
RESULTS_PATH = config.REPORTS_DIR / "buyer_history_lag_experiment.json"


def evaluate_lag(connection, lag_days):
    """Build features with one gap, train LightGBM and score the validation year."""
    features_path = config.ML_DATA_DIR / f"single_bid_features_lag_{lag_days}.parquet"
    build_feature_table(connection, features_path, history_lag_days=lag_days)
    splits = split_by_year(load_features(features_path))
    model = train_lightgbm(splits["train"], splits["validation"])

    validation = splits["validation"]
    scores = model.predict_proba(validation[FEATURES])[:, 1]
    metrics = classification_metrics(validation[TARGET], scores)
    metrics["best_iteration"] = int(model.best_iteration_)
    metrics["share_with_history"] = float((validation["buyer_prior_awards"] > 0).mean())

    features_path.unlink()  # temporary file, about 60 MB
    return metrics


def main():
    results = {}
    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        for lag_days in LAGS_TO_TEST:
            print(f"\nGap of {lag_days} days")
            results[lag_days] = evaluate_lag(connection, lag_days)

    print(f"\nValidation year {config.VALIDATION_YEAR}:")
    print(f"  {'gap (days)':>10} {'ROC-AUC':>8} {'PR-AUC':>8} {'Brier':>8} {'Lift@10%':>9} {'has history':>12}")
    for lag_days, metrics in results.items():
        print(f"  {lag_days:>10} {metrics['roc_auc']:>8.3f} {metrics['pr_auc']:>8.3f} {metrics['brier']:>8.4f} "
              f"{metrics['lift_top_10pct']:>8.2f}x {metrics['share_with_history']:>11.1%}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved {RESULTS_PATH.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
