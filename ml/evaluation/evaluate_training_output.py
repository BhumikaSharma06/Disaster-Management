"""Evaluate a completed training run and write real comparison results."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from ml.evaluation.metrics import evaluate, write_comparison_markdown

ROOT = Path(__file__).resolve().parents[2]
TRAINING_OUTPUT = ROOT / "ml" / "training" / "training_output.json"
RESULTS_JSON = ROOT / "ml" / "evaluation" / "results" / "metrics.json"
RESULTS_MARKDOWN = ROOT / "ml" / "evaluation" / "results" / "metrics.md"


def main() -> int:
    if not TRAINING_OUTPUT.is_file():
        print(
            f"Missing training output: {TRAINING_OUTPUT.relative_to(ROOT)}; "
            "run training with real data first.",
            file=sys.stderr,
        )
        return 2
    payload = json.loads(TRAINING_OUTPUT.read_text(encoding="utf-8"))
    comparison: dict[str, object] = {"stations": {}}
    for station_id, lead_results in payload["stations"].items():
        station_comparison: dict[str, object] = {}
        for lead, values in lead_results.items():
            lead_hours = int(lead)
            y_true = np.asarray(values["test_labels"], dtype=int)
            y_pred = np.asarray(values["prediction"], dtype=int)
            probability = np.asarray(values["probability"], dtype=float)
            index = pd.DatetimeIndex(values["test_index"])

            xgboost_metrics = evaluate(y_true, y_pred, probability, index, lead_hours)
            persistence_predictions = np.asarray(values["persistence"], dtype=int)
            persistence_metrics = evaluate(
                y_true,
                persistence_predictions,
                persistence_predictions.astype(float),
                index,
                lead_hours,
            )

            rule = values.get("rule_threshold")
            rule_metrics = None
            if rule is not None:
                rule_predictions = np.asarray(rule, dtype=int)
                rule_metrics = evaluate(
                    y_true,
                    rule_predictions,
                    rule_predictions.astype(float),
                    index,
                    lead_hours,
                )

            station_comparison[lead] = {
                **xgboost_metrics,
                "persistence_precision": persistence_metrics["precision"],
                "persistence_recall_pod": persistence_metrics["recall_pod"],
                "persistence_false_alarm_ratio": persistence_metrics["false_alarm_ratio"],
                "persistence_f1": persistence_metrics["f1"],
                "rule_threshold": rule_metrics,
            }
        comparison["stations"][station_id] = station_comparison

    write_comparison_markdown(comparison, RESULTS_JSON, RESULTS_MARKDOWN)
    print(f"Wrote {RESULTS_JSON.relative_to(ROOT)} and {RESULTS_MARKDOWN.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
