"""Simple real-data baselines for gauge exceedance forecasting."""

from __future__ import annotations

import pandas as pd


def persistence_baseline(stage: pd.Series, danger_level: float) -> pd.Series:
    """Forecast that current stage persists over every configured lead time."""
    if danger_level is None:
        raise ValueError("A real danger_level must be supplied")
    return (stage.astype(float) > float(danger_level)).astype(int)


def rainfall_upstream_rule(rainfall: pd.Series, upstream_discharge: pd.Series,
                           rain_threshold: float, upstream_threshold: float,
                           index: pd.DatetimeIndex) -> pd.Series:
    """A transparent threshold baseline using only values available at or before t.

    TODO thresholds must be derived from supplied historical real data or supplied
    operational guidance. This function never guesses a threshold.
    """
    if rain_threshold is None or upstream_threshold is None:
        raise ValueError("rain_threshold and upstream_threshold are required")
    rain = rainfall.reindex(index, method="ffill").shift(freq="24h")
    upstream = upstream_discharge.reindex(index, method="ffill").shift(freq="24h")
    return ((rain > float(rain_threshold)) & (upstream > float(upstream_threshold))).astype(int)
