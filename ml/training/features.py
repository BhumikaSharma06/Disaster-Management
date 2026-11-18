"""Build past-only station features and future exceedance labels."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def _past_value(
    values: pd.Series, forecast_index: pd.DatetimeIndex, lag: pd.Timedelta
) -> pd.Series:
    """Get the most recent value at or before each forecast time minus its lag."""
    source = values.dropna().sort_index()
    query = forecast_index - lag
    result = source.reindex(query, method="ffill")
    result.index = forecast_index
    return result


def _labels_within_horizon(
    values: pd.Series, forecast_index: pd.DatetimeIndex, lead_hours: int, threshold: float
) -> pd.Series:
    """Label any observed threshold exceedance in (t, t + lead], masking incomplete windows."""
    observations = values.dropna().sort_index()
    if observations.empty:
        return pd.Series(pd.NA, index=forecast_index, dtype="Int64")

    times = observations.index
    numeric = observations.to_numpy(dtype=float)
    exceedances = numeric > threshold
    time_ns = times.asi8
    forecast_ns = forecast_index.asi8
    cadence_ns = int(pd.Series(np.diff(time_ns)).median()) if len(time_ns) > 1 else 0
    lead_ns = pd.Timedelta(value=int(lead_hours), unit="h").value
    if cadence_ns <= 0:
        return pd.Series(pd.NA, index=forecast_index, dtype="Int64")

    prefix_exceedances = np.concatenate(([0], np.cumsum(exceedances, dtype=np.int64)))
    labels = np.full(len(forecast_index), -1, dtype=np.int8)
    for position, forecast_time in enumerate(forecast_ns):
        horizon_end = forecast_time + lead_ns
        if horizon_end > time_ns[-1]:
            continue
        first = int(np.searchsorted(time_ns, forecast_time, side="right"))
        after_last = int(np.searchsorted(time_ns, horizon_end, side="right"))
        observed_count = after_last - first
        expected_count = max(1, int(round(lead_ns / cadence_ns)))
        if observed_count < expected_count:
            continue
        labels[position] = int(
            prefix_exceedances[after_last] - prefix_exceedances[first] > 0
        )

    result = pd.Series(pd.array(labels, dtype="Int64"), index=forecast_index)
    result = result.mask(result == -1, pd.NA)
    return result


def _add_measurement_lags(
    features: pd.DataFrame,
    gauge: pd.DataFrame,
    column: str,
    prefix: str,
) -> None:
    if column not in gauge or gauge[column].notna().sum() == 0:
        return
    values = pd.to_numeric(gauge[column], errors="coerce").astype(float)
    features[f"{prefix}_now"] = values.reindex(features.index)
    for days in (1, 3, 7):
        features[f"{prefix}_lag_{days}d"] = _past_value(
            values, features.index, pd.Timedelta(value=int(days), unit="D")
        )
    features[f"{prefix}_change_24h"] = (
        values.reindex(features.index)
        - _past_value(values, features.index, pd.Timedelta(value=1, unit="D"))
    )


def build_features(
    gauge: pd.DataFrame,
    rainfall: pd.DataFrame | None,
    upstream: pd.DataFrame | None,
    lead_hours: Iterable[int] = (24, 48, 72),
    danger_level: float | None = None,
    target_variable: str = "stage",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build features for a previously selected station.

    Features only use measurements at or before their forecast timestamp.
    Labels inspect future target observations in the requested lead-time window.
    ``target_variable`` is ``stage`` or ``discharge``; a missing feature source
    (such as rainfall) is omitted rather than replaced with invented values.
    """
    if danger_level is None:
        raise ValueError("A verified danger_level is required from station configuration")
    if target_variable not in {"stage", "discharge"}:
        raise ValueError("target_variable must be 'stage' or 'discharge'")
    if target_variable not in gauge.columns:
        raise KeyError(f"Target variable {target_variable!r} is missing from selected station data")

    gauge = gauge.copy().sort_index()
    gauge = gauge.loc[~gauge.index.duplicated(keep="last")]
    target = pd.to_numeric(gauge[target_variable], errors="coerce").dropna()
    if target.empty:
        raise ValueError(f"No valid observations for target variable {target_variable!r}")

    features = pd.DataFrame(index=target.index)
    _add_measurement_lags(features, gauge, "stage", "stage")
    _add_measurement_lags(features, gauge, "discharge", "discharge")

    if rainfall is not None and not rainfall.empty and "rainfall" in rainfall:
        rain = pd.to_numeric(rainfall["rainfall"], errors="coerce").dropna().sort_index()
        if not rain.empty:
            daily_rain = rain.resample("1D").sum(min_count=1)
            for days in (1, 3, 7):
                rolling_sum = daily_rain.rolling(window=days, min_periods=days).sum()
                features[f"rainfall_sum_{days}d"] = _past_value(
                    rolling_sum, features.index, pd.Timedelta(value=1, unit="D")
                )

    if upstream is not None and not upstream.empty:
        upstream_column = "discharge"
        if upstream_column in upstream and upstream[upstream_column].notna().any():
            flow = pd.to_numeric(upstream[upstream_column], errors="coerce")
            for days in (1, 3, 7):
                features[f"upstream_discharge_lag_{days}d"] = _past_value(
                    flow,
                    features.index,
                    pd.Timedelta(value=int(days), unit="D"),
                )

    features["day_of_year"] = features.index.dayofyear
    features["monsoon_indicator"] = features.index.month.isin([6, 7, 8, 9]).astype(int)

    labels = pd.DataFrame(index=features.index)
    for lead in lead_hours:
        labels[f"exceed_next_{lead}h"] = _labels_within_horizon(
            target, features.index, int(lead), float(danger_level)
        )

    valid = features.notna().all(axis=1) & labels.notna().all(axis=1)
    clean_features = features.loc[valid].replace([np.inf, -np.inf], np.nan).dropna()
    clean_labels = labels.loc[clean_features.index].astype("int64")
    return clean_features, clean_labels


def stage_persistence_at_lead(stage: pd.Series, lead_hours: int) -> pd.Series:
    """Persistence forecast: the current stage is assumed to persist."""
    del lead_hours
    return stage.astype(float)
