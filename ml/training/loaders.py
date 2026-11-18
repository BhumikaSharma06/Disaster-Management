"""Load locally supplied flood observations into a canonical station table."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

logger = logging.getLogger(__name__)

CANONICAL_COLUMNS = [
    "station_name",
    "district",
    "block",
    "river",
    "basin",
    "stage",
    "discharge",
]
TIME_COLUMNS = ("datetime", "timestamp", "date", "time", "data acquisition time")
STAGE_COLUMNS = (
    "river water level telemetry hourly (meter)",
    "stage",
    "water_level",
    "river_stage",
    "gauge_level",
)
DISCHARGE_COLUMNS = ("discharge (m3/s)", "discharge", "flow", "river_discharge")


def _column_name(frame: pd.DataFrame, names: Sequence[str]) -> str | None:
    """Find a source column by case-insensitive exact header match."""
    columns = {str(column).strip().casefold(): str(column) for column in frame.columns}
    for name in names:
        if name.casefold() in columns:
            return columns[name.casefold()]
    return None


def _parse_source_times(values: pd.Series, column_name: str) -> pd.Series:
    """Parse the supplied date formats without assuming an undocumented timezone."""
    if column_name.strip().casefold() == "data acquisition time":
        parsed = pd.to_datetime(
            values, format="%d-%m-%Y %H:%M", errors="coerce", dayfirst=True
        )
    elif column_name.strip().casefold() == "date":
        parsed = pd.to_datetime(values, format="%d-%m-%Y", errors="coerce", dayfirst=True)
    else:
        parsed = pd.to_datetime(values, errors="coerce", format="mixed", dayfirst=True)
    if parsed.isna().any():
        examples = values.loc[parsed.isna()].head(3).tolist()
        raise ValueError(f"Unparseable values in time column {column_name!r}: {examples}")
    return parsed


def _normalise_source_frame(frame: pd.DataFrame, source: Path) -> pd.DataFrame:
    """Map known Bihar telemetry and daily-discharge headers to canonical names."""
    time_column = _column_name(frame, TIME_COLUMNS)
    if time_column is None:
        raise ValueError(f"No supported time column found in {source.name}: {list(frame.columns)}")

    station_column = _column_name(frame, ("site", "station", "station_name"))
    stage_column = _column_name(frame, STAGE_COLUMNS)
    discharge_column = _column_name(frame, DISCHARGE_COLUMNS)
    if station_column is None:
        raise ValueError(f"No station/site name column found in {source.name}")
    if stage_column is None and discharge_column is None:
        raise ValueError(f"No supported stage or discharge measurement found in {source.name}")

    district_column = _column_name(frame, ("station_district", "district"))
    block_column = _column_name(frame, ("station_block", "block"))
    river_column = _column_name(frame, ("river",))
    basin_column = _column_name(frame, ("basin",))

    normalized = pd.DataFrame(index=frame.index)
    normalized["datetime"] = _parse_source_times(frame[time_column], time_column)
    normalized["station_name"] = frame[station_column].astype("string").str.strip()
    normalized["district"] = (
        frame[district_column].astype("string").str.strip()
        if district_column
        else pd.NA
    )
    normalized["block"] = (
        frame[block_column].astype("string").str.strip()
        if block_column
        else pd.NA
    )
    normalized["river"] = (
        frame[river_column].astype("string").str.strip()
        if river_column
        else pd.NA
    )
    normalized["basin"] = (
        frame[basin_column].astype("string").str.strip()
        if basin_column
        else pd.NA
    )
    normalized["stage"] = (
        pd.to_numeric(frame[stage_column], errors="coerce")
        if stage_column
        else float("nan")
    )
    normalized["discharge"] = (
        pd.to_numeric(frame[discharge_column], errors="coerce")
        if discharge_column
        else float("nan")
    )
    normalized = normalized[normalized["station_name"].notna()]
    normalized = normalized[normalized["station_name"].str.casefold() != ""]
    normalized = normalized.set_index("datetime").sort_index()
    return normalized[CANONICAL_COLUMNS]


def _matches_station_filters(
    raw: pd.DataFrame, station_filters: Sequence[Mapping[str, object]]
) -> pd.Series:
    """Select rows matching any configured station by its source name and metadata."""
    station_column = _column_name(raw, ("site", "station", "station_name"))
    if station_column is None:
        return pd.Series(False, index=raw.index)

    source_fields = {
        "district": _column_name(raw, ("station_district", "district")),
        "block": _column_name(raw, ("station_block", "block")),
        "river": _column_name(raw, ("river",)),
        "basin": _column_name(raw, ("basin",)),
    }
    matches = pd.Series(False, index=raw.index)
    for station in station_filters:
        station_name = station.get("source_station_name")
        if not station_name:
            continue
        selected = raw[station_column].astype("string").str.strip().str.casefold() == str(
            station_name
        ).strip().casefold()
        for field, column in source_fields.items():
            expected = station.get(field)
            if expected is not None and column is not None:
                selected &= (
                    raw[column].astype("string").str.strip().str.casefold()
                    == str(expected).strip().casefold()
                )
        matches |= selected.fillna(False)
    return matches.fillna(False)


def _read_frame(path: Path) -> pd.DataFrame:
    """Read supported local tabular data; never fetch remote data."""
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported gauge format: {path.suffix} ({path})")


def _resolve_files(paths: Iterable[str | Path], base: Path) -> list[Path]:
    resolved: list[Path] = []
    missing: list[Path] = []
    for item in paths:
        path = Path(item)
        if not path.is_absolute():
            path = base / path
        (resolved if path.is_file() else missing).append(path)
    if missing:
        raise FileNotFoundError(
            "Missing real data file(s): " + ", ".join(str(path) for path in missing)
        )
    return resolved


def _log_missing(frame: pd.DataFrame, source: str) -> None:
    percentages = frame[["stage", "discharge"]].isna().mean().mul(100)
    missing = percentages[percentages > 0].round(3).to_dict()
    if missing:
        logger.info("Missing measurement values for %s: %s", source, missing)


def _combine_station_rows(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        empty = pd.DataFrame(columns=CANONICAL_COLUMNS)
        empty.index = pd.DatetimeIndex([], name="datetime")
        return empty
    combined = pd.concat(frames).sort_index()
    keys = ["station_name", "district", "block", "river", "basin"]
    if combined.index.has_duplicates:
        reset = combined.reset_index()
        group_keys = ["datetime", *keys]
        value_counts = reset.groupby(group_keys, dropna=False)[
            ["stage", "discharge"]
        ].nunique(dropna=True)
        if (value_counts.to_numpy() > 1).any():
            raise ValueError(
                "Conflicting duplicate measurements exist for a station/timestamp; "
                "inspect the source files instead of averaging them."
            )
        combined = (
            reset.groupby(group_keys, dropna=False, as_index=False)[["stage", "discharge"]]
            .first()
            .set_index("datetime")
            .sort_index()
        )
    return combined[CANONICAL_COLUMNS]


def load_gauge_data(
    file_paths: Iterable[str | Path],
    raw_dir: str | Path,
    station_filters: Sequence[Mapping[str, object]] | None = None,
) -> pd.DataFrame:
    """Load telemetry and manual-discharge files into a multi-station table.

    Canonical columns are station metadata plus nullable ``stage`` and
    ``discharge`` values. The datetime index remains timezone-naive when source
    files do not specify a timezone; callers must not infer one from this loader.
    """
    frames: list[pd.DataFrame] = []
    for path in _resolve_files(file_paths, Path(raw_dir)):
        raw = _read_frame(path)
        if station_filters:
            raw = raw.loc[_matches_station_filters(raw, station_filters)]
            if raw.empty:
                logger.info("No configured station rows found in %s", path.name)
                continue
        frame = _normalise_source_frame(raw, path)
        _log_missing(frame, path.name)
        frames.append(frame)
    return _combine_station_rows(frames)


def load_rainfall(
    file_paths: Iterable[str | Path],
    raw_dir: str | Path,
    aggregate: str = "catchment",
) -> pd.DataFrame:
    """Load local IMD/xarray-compatible rainfall; an empty path list means unavailable."""
    paths = _resolve_files(file_paths, Path(raw_dir))
    if not paths:
        return pd.DataFrame(
            columns=["rainfall"], index=pd.DatetimeIndex([], name="datetime")
        )

    import xarray as xr

    del aggregate  # Spatial catchment averages need configured basin polygons.
    frames: list[pd.DataFrame] = []
    for path in paths:
        if path.suffix.casefold() in {".bin", ".dat", ".gz"}:
            raise ValueError(
                f"IMD binary/archive format needs a source-specific decoder: {path}"
            )
        dataset = xr.open_dataset(path)
        try:
            time_name = next(
                (name for name in ("time", "Time", "datetime") if name in dataset.coords),
                None,
            )
            rain_name = next(
                (
                    name
                    for name in ("rain", "rainfall", "precip", "precipitation")
                    if name in dataset.data_vars
                ),
                None,
            )
            if time_name is None or rain_name is None:
                raise ValueError(
                    f"Rainfall file must expose a time coordinate and rain variable: {path}"
                )
            rainfall = dataset[rain_name]
            spatial_dims = [dim for dim in rainfall.dims if dim != time_name]
            series = (
                rainfall.mean(dim=spatial_dims, skipna=True).to_series()
                if spatial_dims
                else rainfall.to_series()
            )
            series.index = pd.DatetimeIndex(series.index, name="datetime")
            frames.append(series.rename("rainfall").to_frame().sort_index())
        finally:
            dataset.close()
    result = pd.concat(frames).sort_index()
    if result.index.has_duplicates:
        result = result.groupby(level=0).mean(numeric_only=True)
    missing_percent = result.isna().mean().mul(100)
    if missing_percent.any():
        logger.info(
            "Missing rainfall values: %s",
            missing_percent[missing_percent > 0].round(3).to_dict(),
        )
    return result


def load_upstream_discharge(
    file_paths: Iterable[str | Path],
    raw_dir: str | Path,
    station_filters: Sequence[Mapping[str, object]] | None = None,
) -> pd.DataFrame:
    """Load discharge observations using the same normalized source schema."""
    return load_gauge_data(file_paths, raw_dir, station_filters)
