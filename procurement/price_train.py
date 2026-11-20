"""Train and evaluate the fair price model.

Predicts the award value of a contract before it is published, as a range:
the 10th, 50th (expected value) and 90th percentiles. Models, all trained on
2019-2020 and compared on 2021:
  1. baseline  - median award value of similar contracts (sector x country x type)
  2. linear    - ridge regression on the log value
  3. lightgbm  - one gradient-boosted model per percentile (quantile loss)

The test year (2022) is scored once, at the end. Awards far outside the
predicted range are flagged as unusual prices.

Usage (after python -m procurement.price_features):
    python -m procurement.price_train
"""
import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

from procurement import config
from procurement.evaluate import interval_metrics, regression_metrics
from procurement.explain import global_importance, plot_importance, shap_values
from procurement.features import split_by_year
from procurement.price_features import (CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, TARGET,
                                        load_price_features)
from procurement.train import EARLY_STOPPING_ROUNDS, LIGHTGBM_PARAMETERS, build_linear_preprocessing

# Peer groups for the baseline, from most to least specific. A contract whose
# exact group never appeared in training falls back to the next, broader group.
PEER_GROUPS = [
    ["cpv_division", "buyer_country", "contract_type"],
    ["cpv_division", "contract_type"],
]


class PeerMedianBaseline:
    """Predicts the median log award value of similar contracts in the training data."""

    def fit(self, frame):
        self.overall_median = frame[TARGET].median()
        self.group_medians = []
        for columns in PEER_GROUPS:
            medians = frame.groupby(columns, observed=True)[TARGET].median().rename("peer_median")
            self.group_medians.append((columns, medians))
        return self

    def predict(self, frame):
        prediction = pd.Series(np.nan, index=frame.index)
        for columns, medians in self.group_medians:
            matched = frame[columns].join(medians, on=columns)["peer_median"]
            prediction = prediction.fillna(matched)
        return prediction.fillna(self.overall_median).to_numpy()


def build_linear_regression():
    preprocessing = build_linear_preprocessing(CATEGORICAL_FEATURES, NUMERIC_FEATURES)
    return Pipeline([("preprocessing", preprocessing), ("model", Ridge(alpha=1.0))])


def train_quantile_model(train, validation, quantile):
    """LightGBM trained with quantile (pinball) loss for one percentile.

    Quantile loss punishes under- and over-prediction unequally: for the 90th
    percentile, predicting too low costs 9 times more than predicting too high,
    so the model settles where about 90% of actual values fall below it.
    """
    parameters = dict(LIGHTGBM_PARAMETERS, objective="quantile", alpha=quantile)
    model = lgb.LGBMRegressor(**parameters)
    model.fit(
        train[FEATURES],
        train[TARGET],
        eval_X=validation[FEATURES],
        eval_y=validation[TARGET],
        eval_metric="quantile",
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False), lgb.log_evaluation(500)],
    )
    return model


def predict_range(models, frame):
    """Predicted 10th, 50th and 90th percentiles (log scale), one column each.

    The three models are trained separately, so for a few rows their outputs can
    cross (e.g. 10th above 50th). Sorting each row restores the order.
    """
    predictions = np.column_stack([models[quantile].predict(frame[FEATURES]) for quantile in config.PRICE_QUANTILES])
    predictions = np.sort(predictions, axis=1)
    return pd.DataFrame(predictions, columns=["log_p10", "log_p50", "log_p90"], index=frame.index)


def flag_unusual_prices(log_actual, predicted_range, factor=config.PRICE_ANOMALY_FACTOR):
    """'high' if the award is more than `factor` times the 90th percentile,
    'low' if below the 10th percentile divided by `factor`, otherwise 'expected'."""
    log_factor = np.log(factor)
    flags = np.full(len(log_actual), "expected", dtype=object)
    flags[np.asarray(log_actual) > predicted_range["log_p90"].to_numpy() + log_factor] = "high"
    flags[np.asarray(log_actual) < predicted_range["log_p10"].to_numpy() - log_factor] = "low"
    return flags


def estimate_segments(frame):
    """Row masks for reporting: is a usable estimate available, and does it equal the award?"""
    has_estimate = frame["log_estimated_value"].notna()
    equals_award = frame["estimate_equals_award"].astype("boolean").fillna(False).astype(bool)
    return {
        "all": pd.Series(True, index=frame.index),
        "estimate_differs_from_award": has_estimate & ~equals_award,
        "estimate_equals_award": has_estimate & equals_award,
        "no_estimate": ~has_estimate,
    }


def print_point_metrics(results, split_name):
    print(f"\n{split_name}:")
    print(f"  {'model':<10} {'MAE(log)':>9} {'median % error':>15} {'within 25%':>11} {'within 2x':>10} {'R2(log)':>8}")
    for model_name, by_split in results.items():
        metrics = by_split[split_name]
        print(f"  {model_name:<10} {metrics['mae_log']:>9.3f} {metrics['median_abs_pct_error']:>15.1%} "
              f"{metrics['within_25pct']:>11.1%} {metrics['within_factor_2']:>10.1%} {metrics['r2_log']:>8.3f}")


def main():
    splits = split_by_year(load_price_features())
    for name, frame in splits.items():
        median_value = np.exp(frame[TARGET].median())
        print(f"{name:<11} {len(frame):>9,} awards, median value EUR {median_value:,.0f}")
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]

    print("\nTraining baseline")
    baseline = PeerMedianBaseline().fit(train)

    print("Training linear regression")
    linear = build_linear_regression()
    linear.fit(train[FEATURES], train[TARGET])

    quantile_models = {}
    for quantile in config.PRICE_QUANTILES:
        print(f"Training LightGBM, percentile {quantile:.0%}")
        quantile_models[quantile] = train_quantile_model(train, validation, quantile)
        print(f"  best iteration: {quantile_models[quantile].best_iteration_}")

    point_predictions = {
        "baseline": baseline.predict,
        "linear": lambda frame: linear.predict(frame[FEATURES]),
        "lightgbm": lambda frame: predict_range(quantile_models, frame)["log_p50"].to_numpy(),
    }
    results = {}
    for model_name, predict in point_predictions.items():
        results[model_name] = {}
        for split_name in ["validation", "test"]:
            frame = splits[split_name]
            results[model_name][split_name] = regression_metrics(frame[TARGET], predict(frame))
    print_point_metrics(results, "validation")
    print_point_metrics(results, "test")

    test_range = predict_range(quantile_models, test)
    print("\nLightGBM on the test year by estimate availability:")
    print(f"  {'segment':<28} {'share':>6} {'median % error':>15} {'within 2x':>10} {'80% range coverage':>19}")
    segment_results = {}
    for segment_name, mask in estimate_segments(test).items():
        segment = test[mask]
        point = regression_metrics(segment[TARGET], test_range.loc[mask, "log_p50"])
        interval = interval_metrics(segment[TARGET], test_range.loc[mask, "log_p10"], test_range.loc[mask, "log_p90"])
        segment_results[segment_name] = {"share": float(mask.mean()), **point, **interval}
        print(f"  {segment_name:<28} {mask.mean():>6.1%} {point['median_abs_pct_error']:>15.1%} "
              f"{point['within_factor_2']:>10.1%} {interval['coverage']:>19.1%}")

    interval = segment_results["all"]
    print(f"\n80% range: median width {interval['median_width_ratio']:.1f}x (90th / 10th percentile)")

    flags = flag_unusual_prices(test[TARGET], test_range)
    flag_shares = {flag: float(np.mean(flags == flag)) for flag in ["high", "low"]}
    print(f"Unusual prices in the test year (more than {config.PRICE_ANOMALY_FACTOR:.0f}x outside the range): "
          f"{flag_shares['high']:.1%} high, {flag_shares['low']:.1%} low")

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for quantile, model in quantile_models.items():
        model.booster_.save_model(config.MODELS_DIR / f"price_p{quantile * 100:.0f}.txt")

    sample = test.sample(50_000, random_state=config.RANDOM_SEED)
    values, _ = shap_values(quantile_models[0.5].booster_, sample, FEATURES)
    importance = global_importance(values)
    print("\nMean |SHAP| per feature (median model, log scale):")
    print(importance.to_string(float_format=lambda value: f"{value:.3f}"))
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plot_importance(importance, config.FIGURES_DIR / "price_shap_importance.png",
                    title="What drives the expected award value (test year 2022)",
                    x_label="Mean |SHAP value| (log of award value)")

    report = {
        "split": {"train": f"published up to {config.TRAIN_END_YEAR}",
                  "validation": str(config.VALIDATION_YEAR), "test": str(config.TEST_YEAR)},
        "population": "awarded contracts with a plausible value, excluding framework agreements",
        "best_iterations": {f"p{quantile * 100:.0f}": int(model.best_iteration_)
                            for quantile, model in quantile_models.items()},
        "metrics": results,
        "test_by_estimate_segment": segment_results,
        "test_unusual_price_shares": flag_shares,
        "test_shap_importance": importance.round(4).to_dict(),
    }
    config.PRICE_METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved models to {config.MODELS_DIR.relative_to(config.PROJECT_ROOT)}/ and metrics to "
          f"{config.PRICE_METRICS_PATH.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
