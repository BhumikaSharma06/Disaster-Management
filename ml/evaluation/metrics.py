"""Classification and warning-timing metrics for flood exceedance forecasts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def false_alarm_ratio(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Return false alarms divided by the sum of false alarms and hits."""
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    false_alarm = int(matrix[0, 1])
    hits = int(matrix[1, 1])
    return false_alarm / (false_alarm + hits) if false_alarm + hits else 0.0


def warning_lead_time_hours(index: pd.DatetimeIndex, y_true: np.ndarray,
                            y_pred: np.ndarray, lead_hours: int) -> float:
    """Average first correct-warning lead time before independently defined exceedances."""
    del lead_hours
    lead_times: list[float] = []
    true_indices = np.flatnonzero(y_true == 1)
    for true_position in true_indices:
        warning_positions = np.flatnonzero(y_pred[:true_position + 1] == 1)
        if warning_positions.size:
            first_warning = warning_positions[-1]
            lead = (index[true_position] - index[first_warning]).total_seconds() / 3600
            lead_times.append(lead)
    return float(np.mean(lead_times)) if lead_times else 0.0


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, probability: np.ndarray,
             index: pd.DatetimeIndex, lead_hours: int) -> dict[str, object]:
    """Calculate the required metrics; each input must contain real observations."""
    if y_true.size == 0:
        raise ValueError("Cannot evaluate an empty real-data test set")
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall_pod": float(recall_score(y_true, y_pred, zero_division=0)),
        "false_alarm_ratio": false_alarm_ratio(y_true, y_pred),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true, probability)
                        if len(np.unique(y_true)) > 1 else 0.0),
        "confusion_matrix": matrix,
        "warning_lead_time_hours": warning_lead_time_hours(index, y_true, y_pred, lead_hours),
    }


def write_comparison_markdown(results: dict[str, object], output_json: Path,
                              output_markdown: Path) -> None:
    """Write real comparison data without synthetic placeholder rows."""
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Baseline vs XGBoost comparison",
        "",
        "| Station | Lead | Model | Precision | Recall/POD | FAR | F1 | "
        "PR-AUC | Warning lead hours |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for station, leads in results.get("stations", {}).items():
        for lead, values in leads.items():
            lines.append(
                f"| {station} | {lead} | Persistence | "
                f"{values['persistence_precision']:.4f} | "
                f"{values['persistence_recall_pod']:.4f} | "
                f"{values['persistence_false_alarm_ratio']:.4f} | "
                f"{values['persistence_f1']:.4f} | 0.0000 | N/A |"
            )
            rule = values.get("rule_threshold")
            if rule is not None:
                lines.append(
                    f"| {station} | {lead} | Rain/upstream rule | "
                    f"{rule['precision']:.4f} | {rule['recall_pod']:.4f} | "
                    f"{rule['false_alarm_ratio']:.4f} | {rule['f1']:.4f} | "
                    "0.0000 | N/A |"
                )
            lines.append(
                f"| {station} | {lead} | XGBoost | "
                f"{values['precision']:.4f} | {values['recall_pod']:.4f} | "
                f"{values['false_alarm_ratio']:.4f} | {values['f1']:.4f} | "
                f"{values['pr_auc']:.4f} | "
                f"{values['warning_lead_time_hours']:.1f} |"
            )
    output_markdown.write_text("\n".join(lines), encoding="utf-8")
