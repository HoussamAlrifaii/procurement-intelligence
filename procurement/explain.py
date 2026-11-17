"""Explain the single-bid model with SHAP values.

A SHAP value is one feature's contribution to one prediction: starting from the
average prediction, how far did this feature push the risk up or down? The
contributions of all features add up exactly to the model's output (in log-odds,
the scale the model works on before the sigmoid turns it into a probability).

LightGBM computes exact SHAP values for its own trees (TreeSHAP) with
predict(..., pred_contrib=True), so no extra library is needed.

Usage (after python -m procurement.train):
    python -m procurement.explain
"""
import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")  # write image files without opening a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from procurement import config
from procurement.features import FEATURES, TARGET, load_features, split_by_year

MODEL_PATH = config.MODELS_DIR / "single_bid_lightgbm.txt"
SAMPLE_SIZE = 50_000

FEATURE_LABELS = {
    "buyer_country": "Country",
    "buyer_type": "Buyer type",
    "buyer_main_activity": "Buyer activity",
    "contract_type": "Contract type",
    "procedure_type": "Procedure",
    "award_criterion": "Award criterion",
    "cpv_division": "Sector (CPV division)",
    "is_framework_agreement": "Framework agreement",
    "is_eu_funded": "EU-funded",
    "is_gpa_covered": "Covered by the GPA",
    "used_electronic_auction": "Electronic auction",
    "lots_in_notice": "Lots in notice",
    "log_estimated_value": "Estimated value",
    "publication_month": "Publication month",
    "buyer_prior_awards": "Buyer's earlier awards",
    "buyer_prior_single_bid_rate": "Buyer's earlier single-bid rate",
}


def load_model(path=MODEL_PATH):
    return lgb.Booster(model_file=str(path))


def shap_values(model, frame):
    """SHAP values per row and feature, plus the base value (log-odds).

    pred_contrib returns one column per feature followed by one column with the
    base value: the model's average output before any feature is considered.
    """
    contributions = model.predict(frame[FEATURES], pred_contrib=True)
    values = pd.DataFrame(contributions[:, :-1], columns=FEATURES, index=frame.index)
    base_value = contributions[0, -1]
    return values, base_value


def global_importance(values):
    """Mean absolute SHAP value per feature: how much each feature moves predictions on average."""
    importance = values.abs().mean().sort_values(ascending=False)
    return importance.rename(index=FEATURE_LABELS)


def display_value(name, value):
    """Readable value for an explanation, e.g. the estimate in EUR instead of its log."""
    if pd.isna(value):
        return "not reported"
    if name == "log_estimated_value":
        return f"EUR {np.exp(value):,.0f}"
    if name == "buyer_prior_single_bid_rate":
        return f"{value:.0%}"
    if isinstance(value, float):
        return f"{value:,.0f}"
    return str(value)


def explain_award(model, row):
    """Top reasons behind one prediction, largest effect first.

    `row` is a one-row DataFrame with the feature columns.
    """
    values, base_value = shap_values(model, row)
    contributions = values.iloc[0]
    log_odds = base_value + contributions.sum()
    probability = 1 / (1 + np.exp(-log_odds))

    reasons = pd.DataFrame({
        "feature": [FEATURE_LABELS[name] for name in FEATURES],
        "value": [display_value(name, row.iloc[0][name]) for name in FEATURES],
        "contribution": contributions.to_numpy(),
    })
    reasons["direction"] = np.where(reasons["contribution"] > 0, "raises risk", "lowers risk")
    reasons = reasons.reindex(reasons["contribution"].abs().sort_values(ascending=False).index)
    return probability, reasons.reset_index(drop=True)


def plot_importance(importance, output_path):
    figure, axis = plt.subplots(figsize=(8, 5.5))
    ordered = importance.sort_values()
    axis.barh(ordered.index, ordered.to_numpy(), color="#2B8DE0")
    axis.set_xlabel("Mean |SHAP value| (log-odds)")
    axis.set_title("What drives single-bid risk (test year 2022)", loc="left")
    axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def main():
    model = load_model()
    test = split_by_year(load_features())["test"]
    sample = test.sample(SAMPLE_SIZE, random_state=config.RANDOM_SEED)

    values, base_value = shap_values(model, sample)
    importance = global_importance(values)
    print("Mean |SHAP| per feature, test-year sample:")
    print(importance.to_string(float_format=lambda value: f"{value:.3f}"))

    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figure_path = config.FIGURES_DIR / "single_bid_shap_importance.png"
    plot_importance(importance, figure_path)
    print(f"\nSaved {figure_path.relative_to(config.PROJECT_ROOT)}")

    # A high-risk award as the worked example: these are the cases an auditor reviews.
    predictions = model.predict(sample[FEATURES])
    example = sample[predictions >= 0.8].head(1)
    probability, reasons = explain_award(model, example)
    print(f"\nExample award {example['award_id'].iloc[0]} (actual single-bid: {example[TARGET].iloc[0]}):"
          f" predicted risk {probability:.0%}")
    print(reasons.head(6).to_string(index=False, float_format=lambda value: f"{value:+.3f}"))


if __name__ == "__main__":
    main()
