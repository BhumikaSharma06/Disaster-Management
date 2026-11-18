"""Tests for flood features and 24/48/72-hour labels using SYNTHETIC data only."""

from pathlib import Path

import pandas as pd
from ml.training.features import build_features
from ml.training.loaders import load_gauge_data
from ml.training.train_xgboost import chronological_split_masks

FIXTURE = Path(__file__).parent / "fixtures" / "SYNTHETIC_gauge.csv"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _synthetic_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load clearly synthetic unit-test observations, never real raw data."""
    frame = pd.read_csv(FIXTURE)
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True)
    frame = frame.set_index("datetime").sort_index()
    gauge = frame[["stage", "discharge"]]
    rainfall = frame[["rainfall"]].rename(columns={"rainfall": "rainfall"})
    upstream = frame[["upstream_discharge"]]
    return gauge, rainfall, upstream


def test_features_do_not_change_when_future_stage_changes() -> None:
    gauge, rainfall, upstream = _synthetic_frames()
    features_before, _ = build_features(
        gauge, rainfall, upstream, (24, 48, 72), 12.0
    )

    gauge_changed = gauge.copy()
    gauge_changed.loc[gauge_changed.index[-1], "stage"] = 999.0
    rainfall_changed = rainfall.copy()
    rainfall_changed.loc[rainfall_changed.index[-1], "rainfall"] = 999.0
    upstream_changed = upstream.copy()
    upstream_changed.loc[upstream_changed.index[-1], "upstream_discharge"] = 999.0
    features_after, _ = build_features(
        gauge_changed, rainfall_changed, upstream_changed, (24, 48, 72), 12.0
    )

    shared = features_before.index.intersection(features_after.index)
    changed_timestamp = gauge_changed.index[-1]

    # When a future observation changes, every earlier feature row must remain identical.
    earlier = shared[shared < changed_timestamp]
    pd.testing.assert_frame_equal(features_before.loc[earlier], features_after.loc[earlier])


def test_future_labels_detect_exceedance() -> None:
    gauge, rainfall, upstream = _synthetic_frames()
    _, labels = build_features(gauge, rainfall, upstream, (24, 48, 72), 12.0)

    assert labels.loc[pd.Timestamp("2024-07-14", tz="UTC"), "exceed_next_24h"] == 1
    assert labels.loc[pd.Timestamp("2024-07-13", tz="UTC"), "exceed_next_48h"] == 1
    assert labels.loc[pd.Timestamp("2024-07-12", tz="UTC"), "exceed_next_72h"] == 1


def test_loaders_normalize_supplied_multistation_headers() -> None:
    station_filter = [
        {
            "source_station_name": "Birpur Barrage",
            "district": "Supaul",
            "block": "Birpur",
            "river": "Kosi",
            "basin": "Kosi",
        }
    ]
    gauge = load_gauge_data(
        ["SYNTHETIC_telemetry.csv", "SYNTHETIC_discharge_manual.csv"],
        FIXTURE_DIR,
        station_filters=station_filter,
    )

    assert set(gauge["station_name"].dropna()) == {"Birpur Barrage"}
    assert set(gauge["district"].dropna()) == {"Supaul"}
    assert gauge["discharge"].notna().sum() == 2
    assert gauge["stage"].isna().all()
    assert gauge.index.min() == pd.Timestamp("2024-07-01")
    assert gauge.index.max() == pd.Timestamp("2024-07-02")


def test_telemetry_loader_preserves_multiple_stations_when_unfiltered() -> None:
    gauge = load_gauge_data(["SYNTHETIC_telemetry.csv"], FIXTURE_DIR)

    assert set(gauge["station_name"]) == {"Test Gauge A", "Other Gauge"}
    assert gauge["stage"].notna().sum() == 3
    assert gauge["discharge"].isna().all()


def test_chronological_split_purges_labels_that_could_cross_test_start() -> None:
    index = pd.date_range("2022-01-01", "2025-01-10", freq="D")

    train_mask, test_mask = chronological_split_masks(
        index,
        train_seasons=[2022, 2023],
        test_seasons=[2024, 2025],
        max_lead_hours=72,
    )

    test_start = index[test_mask].min()
    assert index[train_mask].max() + pd.Timedelta(value=72, unit="h") < test_start
    assert index[test_mask].min().year == 2024
