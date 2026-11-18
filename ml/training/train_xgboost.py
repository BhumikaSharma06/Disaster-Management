"""Train time-based, station-specific XGBoost lead-time classifiers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml
from ml.training.baselines import persistence_baseline
from ml.training.features import build_features
from ml.training.loaders import load_gauge_data, load_rainfall, load_upstream_discharge
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def season_mask(index: pd.DatetimeIndex, seasons: list[int | str]) -> pd.Series:
    if not seasons:
        raise ValueError("TODO: configure train/test monsoon seasons in ml/config.yaml")
    masks = []
    for season in seasons:
        try:
            year = int(season)
            masks.append(pd.Series(index.year == year, index=index))
        except ValueError:
            parts = season.split("-")
            if len(parts) != 2:
                raise ValueError(f"Unsupported season format: {season}; use a year or YYYY-YYYY")
            start, end = int(parts[0]), int(parts[1])
            masks.append(pd.Series((index.year >= start) & (index.year <= end), index=index))
    return pd.concat(masks, axis=1).any(axis=1)


def chronological_split_masks(
    index: pd.DatetimeIndex,
    train_seasons: list[int | str],
    test_seasons: list[int | str],
    max_lead_hours: int,
) -> tuple[pd.Series, pd.Series]:
    """Create year-based splits and purge training labels crossing test start."""
    train_mask = season_mask(index, train_seasons)
    test_mask = season_mask(index, test_seasons)
    if not train_mask.any() or not test_mask.any():
        raise ValueError("Configured train/test periods select no rows")
    test_start = index[test_mask].min()
    purge = pd.Timedelta(value=max_lead_hours, unit="h")
    train_mask &= pd.Series(index < test_start - purge, index=index)
    if not train_mask.any():
        raise ValueError(f"No training rows remain after the {purge} pre-test purge")
    if index[train_mask].max() >= test_start - purge:
        raise ValueError("Training labels could overlap the held-out test period")
    return train_mask, test_mask


def train(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    raw_dir = ROOT / config["paths"]["raw"]
    model_dir = ROOT / config["paths"]["models"]

    gauge_files = config["gauge_files"]
    rainfall_files = config.get("rainfall_files", [])
    upstream_files = config.get("upstream_discharge_files", [])
    all_files = gauge_files + rainfall_files + upstream_files
    unresolved = [path for path in all_files if str(path).startswith("TODO_")]
    if unresolved:
        raise FileNotFoundError(
            "Replace TODO file names in ml/config.yaml: " + ", ".join(unresolved)
        )

    stations = config["stations"]
    gauge = load_gauge_data(gauge_files, raw_dir, station_filters=stations)
    rainfall = load_rainfall(rainfall_files, raw_dir)
    upstream = load_upstream_discharge(
        upstream_files, raw_dir, station_filters=config.get("upstream_stations")
    )

    train_seasons = config["train_test_seasons"]["train"]
    test_seasons = config["train_test_seasons"]["test"]
    if not stations:
        raise ValueError("Configure at least one station in ml/config.yaml")

    prepared: list[tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, str]] = []
    for station in stations:
        station_name = station.get("source_station_name")
        if not station_name:
            raise ValueError(
                f"Station {station.get('name', '<unnamed>')} needs source_station_name"
            )
        selected = gauge.loc[
            gauge["station_name"].astype("string").str.casefold()
            == str(station_name).strip().casefold()
        ]
        for metadata_field in ("district", "block", "river", "basin"):
            expected = station.get(metadata_field)
            if expected is not None:
                selected = selected.loc[
                    selected[metadata_field].astype("string").str.casefold()
                    == str(expected).strip().casefold()
                ]
        if selected.empty:
            raise ValueError(
                f"No rows matched station {station_name!r} and its configured metadata"
            )
        target_variable = station.get("target_variable", "stage")
        danger_level = station.get("danger_level")
        if danger_level is None:
            raise ValueError(
                f"Station {station_name!r} has {len(selected)} matching real rows, "
                "but its verified danger_level is missing"
            )
        station_features, station_labels = build_features(
            selected,
            rainfall,
            upstream,
            config["lead_times_hours"],
            danger_level,
            target_variable=target_variable,
        )
        prepared.append(
            (station, station_features, station_labels, str(target_variable))
        )

    if not train_seasons or not test_seasons:
        raise ValueError(
            "TODO: configure chronological train and test seasons in ml/config.yaml"
        )

    model_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {"stations": {}, "leads": config["lead_times_hours"]}

    for station, features, labels, target_variable in prepared:
        station_name = station["source_station_name"]
        model_key = station.get("station_id") or re.sub(
            r"[^a-z0-9]+", "_", station_name.casefold()
        ).strip("_")
        danger = float(station["danger_level"])
        try:
            train_mask, test_mask = chronological_split_masks(
                features.index,
                train_seasons,
                test_seasons,
                max(config["lead_times_hours"]),
            )
        except ValueError as error:
            raise ValueError(
                f"Invalid chronological split for station {station_name!r}: {error}"
            ) from error

        station_result: dict[str, Any] = {}
        for lead in config["lead_times_hours"]:
            label_col = f"exceed_next_{lead}h"
            y_train = labels.loc[train_mask, label_col].astype(int)
            y_test = labels.loc[test_mask, label_col].astype(int)
            if y_train.nunique() < 2:
                raise ValueError(
                    f"Training labels for station {station_name}, lead {lead}h have one class"
                )

            positives = int(y_train.sum())
            negatives = int(len(y_train) - positives)
            weight = negatives / positives if positives else 1.0
            model = XGBClassifier(
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="binary:logistic",
                eval_metric="aucpr",
                scale_pos_weight=weight,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(features.loc[train_mask], y_train)

            model_path = model_dir / f"{model_key}_lead_{lead}h.joblib"
            joblib.dump(model, model_path)
            probability = model.predict_proba(features.loc[test_mask])[:, 1]
            prediction = (probability >= 0.5).astype(int)

            rule_predictions = None
            rain_threshold = config.get("rainfall_threshold_mm")
            upstream_threshold = config.get("upstream_discharge_threshold")
            if (
                rain_threshold is not None
                and upstream_threshold is not None
                and "rainfall_sum_1d" in features
                and "upstream_discharge_lag_1d" in features
            ):
                rule_predictions = (
                    (features.loc[test_mask, "rainfall_sum_1d"] > float(rain_threshold))
                    & (
                        features.loc[test_mask, "upstream_discharge_lag_1d"]
                        > float(upstream_threshold)
                    )
                ).astype(int).tolist()

            station_result[str(lead)] = {
                "model": model_path.relative_to(ROOT).as_posix(),
                "target_variable": target_variable,
                "danger_level": danger,
                "train_rows": len(y_train),
                "test_rows": len(y_test),
                "persistence": persistence_baseline(
                    features.loc[test_mask, f"{target_variable}_now"], danger
                ).tolist(),
                "rule_threshold": rule_predictions,
                "prediction": prediction.tolist(),
                "probability": probability.tolist(),
                "test_index": [value.isoformat() for value in features.loc[test_mask].index],
                "test_labels": y_test.tolist(),
            }
        results["stations"][model_key] = station_result

    output = ROOT / "ml" / "training" / "training_output.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Kosi flood exceedance models")
    parser.add_argument("--config", type=Path, default=ROOT / "ml" / "config.yaml")
    args = parser.parse_args()
    try:
        train(args.config)
    except (FileNotFoundError, ValueError) as error:
        print(f"Missing real data or configuration: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
