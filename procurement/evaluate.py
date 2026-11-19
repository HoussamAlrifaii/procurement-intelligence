"""Metrics for probability predictions of a binary target."""
import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score, log_loss,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)

LIFT_SHARES = [0.01, 0.05, 0.10, 0.20]


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


def lift_table(y_true, y_score, shares=LIFT_SHARES):
    """Lift at several review budgets: the smaller the reviewed share, the higher the lift."""
    return {f"top_{share:.0%}": float(lift_at_top(y_true, y_score, share)) for share in shares}


def best_f1_threshold(y_true, y_score):
    """Threshold with the highest F1 (balance of precision and recall).

    Chosen on the validation year only, then applied unchanged to the test year.
    """
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)
    # The last precision/recall pair has no threshold, so it is dropped.
    precision = precision[:-1]
    recall = recall[:-1]
    denominator = precision + recall
    f1 = np.divide(2 * precision * recall, denominator, out=np.zeros_like(denominator), where=denominator > 0)
    return float(thresholds[np.argmax(f1)])


def threshold_metrics(y_true, y_score, threshold):
    """Precision, recall and F1 when every row at or above the threshold is flagged."""
    flagged = (np.asarray(y_score) >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "flagged_share": float(flagged.mean()),
        "precision": float(precision_score(y_true, flagged)),
        "recall": float(recall_score(y_true, flagged)),
        "f1": float(f1_score(y_true, flagged)),
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
