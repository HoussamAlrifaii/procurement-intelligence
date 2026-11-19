"""Train and evaluate the single-bid risk models.

Three models, from simplest to strongest, all trained on 2019-2020:
  1. baseline       - each country's historical single-bid rate
  2. logistic       - logistic regression on one-hot categories and scaled numbers
  3. lightgbm       - gradient-boosted trees, stopped early on the 2021 validation year

The validation year (2021) is used to compare models and stop training. The test
year (2022) is scored once, at the end, and never used for any choice.

Usage (after python -m procurement.features):
    python -m procurement.train
"""
import json

import joblib
import lightgbm as lgb
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from procurement import config
from procurement.evaluate import (best_f1_threshold, calibration_table, classification_metrics, lift_table,
                                  threshold_metrics)
from procurement.features import (CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, TARGET,
                                  load_features, split_by_year)

LIGHTGBM_PARAMETERS = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 63,           # maximum leaves per tree: limits how complex one tree can be
    "min_child_samples": 200,   # each leaf needs 200+ awards, so trees cannot fit tiny groups
    "subsample": 0.8,           # each tree sees 80% of the rows ...
    "subsample_freq": 1,
    "colsample_bytree": 0.8,    # ... and 80% of the features, which reduces overfitting
    "n_estimators": 3000,       # upper bound; early stopping picks the real number
    "random_state": config.RANDOM_SEED,
    "verbose": -1,
}
EARLY_STOPPING_ROUNDS = 100


class CountryRateBaseline:
    """Predicts each country's single-bid rate in the training data."""

    def fit(self, frame):
        self.overall_rate = frame[TARGET].mean()
        self.country_rates = frame.groupby("buyer_country", observed=True)[TARGET].mean()
        return self

    def predict_proba(self, frame):
        rates = frame["buyer_country"].map(self.country_rates).astype(float)
        return rates.fillna(self.overall_rate).to_numpy()


def build_logistic_regression():
    """Logistic regression with the preprocessing it needs.

    Unlike trees, a linear model needs categories turned into 0/1 columns
    (one-hot), missing numbers filled in, and numbers on a similar scale so the
    regularisation treats every feature fairly.
    """
    categorical = OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=100)
    numeric = make_pipeline(
        # add_indicator adds a 0/1 column "value was missing", so the model can
        # still learn that a missing estimate is itself informative.
        SimpleImputer(strategy="median", add_indicator=True),
        StandardScaler(),
    )
    preprocessing = ColumnTransformer([
        ("categorical", categorical, CATEGORICAL_FEATURES),
        ("numeric", numeric, NUMERIC_FEATURES),
    ])
    model = LogisticRegression(C=1.0, max_iter=1000)
    return Pipeline([("preprocessing", preprocessing), ("model", model)])


def train_lightgbm(train, validation):
    """Gradient boosting with early stopping on the validation year."""
    model = lgb.LGBMClassifier(**LIGHTGBM_PARAMETERS)
    model.fit(
        train[FEATURES],
        train[TARGET],
        eval_X=validation[FEATURES],
        eval_y=validation[TARGET],
        eval_metric="auc",
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False), lgb.log_evaluation(200)],
    )
    return model


def score(model_name, model, frame):
    if model_name == "baseline":
        return model.predict_proba(frame)
    return model.predict_proba(frame[FEATURES])[:, 1]


def evaluate_models(models, splits, split_names):
    results = {}
    for model_name, model in models.items():
        results[model_name] = {}
        for split_name in split_names:
            frame = splits[split_name]
            results[model_name][split_name] = classification_metrics(frame[TARGET], score(model_name, model, frame))
    return results


def print_results(results, split_name):
    print(f"\n{split_name}:")
    print(f"  {'model':<10} {'ROC-AUC':>8} {'PR-AUC':>8} {'Brier':>8} {'Lift@10%':>9}")
    for model_name, by_split in results.items():
        metrics = by_split[split_name]
        print(f"  {model_name:<10} {metrics['roc_auc']:>8.3f} {metrics['pr_auc']:>8.3f} "
              f"{metrics['brier']:>8.4f} {metrics['lift_top_10pct']:>8.2f}x")


def main():
    splits = split_by_year(load_features())
    for name, frame in splits.items():
        print(f"{name:<11} {len(frame):>9,} awards, single-bid rate {frame[TARGET].mean():.1%}")

    print("\nTraining baseline")
    baseline = CountryRateBaseline().fit(splits["train"])

    print("Training logistic regression")
    logistic = build_logistic_regression()
    logistic.fit(splits["train"][FEATURES], splits["train"][TARGET])

    print("Training LightGBM")
    lightgbm_model = train_lightgbm(splits["train"], splits["validation"])
    print(f"  best iteration: {lightgbm_model.best_iteration_}")

    models = {"baseline": baseline, "logistic": logistic, "lightgbm": lightgbm_model}
    results = evaluate_models(models, splits, ["validation", "test"])
    print_results(results, "validation")
    print_results(results, "test")

    test = splits["test"]
    validation = splits["validation"]
    test_scores = score("lightgbm", lightgbm_model, test)

    # The threshold is chosen on 2021 and only applied to 2022.
    threshold = best_f1_threshold(validation[TARGET], score("lightgbm", lightgbm_model, validation))
    at_threshold = threshold_metrics(test[TARGET], test_scores, threshold)
    print(f"\nLightGBM on the test year, flagging risk >= {threshold:.0%} (best F1 on validation):")
    print(f"  flagged {at_threshold['flagged_share']:.1%} of awards, precision {at_threshold['precision']:.1%}, "
          f"recall {at_threshold['recall']:.1%}, F1 {at_threshold['f1']:.3f}")

    lifts = lift_table(test[TARGET], test_scores)
    print("LightGBM lift by review budget: " + ", ".join(f"{name} {value:.2f}x" for name, value in lifts.items()))

    calibration = calibration_table(test[TARGET], test_scores)
    print("\nLightGBM calibration on the test year:")
    print(calibration.to_string(index=False, float_format=lambda value: f"{value:.3f}"))

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(logistic, config.MODELS_DIR / "single_bid_logistic.joblib")
    lightgbm_model.booster_.save_model(config.MODELS_DIR / "single_bid_lightgbm.txt")

    report = {
        "split": {
            "train": f"published up to {config.TRAIN_END_YEAR}",
            "validation": str(config.VALIDATION_YEAR),
            "test": str(config.TEST_YEAR),
        },
        "population": "awarded contracts in competitive procedures with a known number of offers",
        "lightgbm_best_iteration": int(lightgbm_model.best_iteration_),
        "metrics": results,
        "test_at_validation_threshold": at_threshold,
        "test_lift_by_budget": lifts,
        "test_calibration": calibration.to_dict(orient="records"),
    }
    config.SINGLE_BID_METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved models to {config.MODELS_DIR.relative_to(config.PROJECT_ROOT)}/ and metrics to "
          f"{config.SINGLE_BID_METRICS_PATH.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
