"""Metrics for probability predictions of a binary target."""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def lift_at_top(y_true, y_score, share=0.10):
    """Positive rate among the highest-scored `share` of rows, divided by the overall rate.

    Answers the auditor's question: "if I review only the riskiest 10%, how many
    times more single-bid tenders do I find than by picking at random?"
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    top_count = int(len(y_score) * share)
    top_rows = np.argsort(-y_score)[:top_count]
    return y_true[top_rows].mean() / y_true.mean()


def classification_metrics(y_true, y_score):
    """Ranking, accuracy-of-probability and lift metrics in one dictionary."""
    return {
        "rows": int(len(y_true)),
        "positive_rate": float(np.mean(y_true)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),       # ranking: 0.5 = random
        "pr_auc": float(average_precision_score(y_true, y_score)),  # random = positive_rate
        "brier": float(brier_score_loss(y_true, y_score)),       # mean squared error of probabilities
        "log_loss": float(log_loss(y_true, y_score)),
        "lift_top_10pct": float(lift_at_top(y_true, y_score, 0.10)),
    }


def calibration_table(y_true, y_score, bins=10):
    """Mean predicted probability vs observed rate per decile of the prediction.

    A well-calibrated model has the two columns close together: tenders given
    about 60% risk are single-bid about 60% of the time.
    """
    frame = pd.DataFrame({"actual": np.asarray(y_true), "predicted": np.asarray(y_score)})
    frame["decile"] = pd.qcut(frame["predicted"], bins, labels=False, duplicates="drop") + 1
    table = frame.groupby("decile").agg(
        rows=("actual", "size"),
        mean_predicted=("predicted", "mean"),
        observed_rate=("actual", "mean"),
    )
    return table.reset_index()
