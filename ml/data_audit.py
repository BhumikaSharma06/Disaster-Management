"""Audit local real datasets under ml/data/raw and write a Markdown report."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "ml" / "data" / "raw"
REPORT = ROOT / "docs" / "data_audit_report.md"


def _readable_tabular(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported tabular format: {suffix}")


def _date_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns
            if str(column).strip().lower()
            in {"datetime", "timestamp", "date", "time", "data acquisition time"}]


def _parse_dates(values: pd.Series, column_name: str) -> pd.Series:
    if column_name.strip().lower() == "data acquisition time":
        return pd.to_datetime(
            values, format="%d-%m-%Y %H:%M", errors="coerce", dayfirst=True
        )
    if column_name.strip().lower() == "date":
        return pd.to_datetime(values, format="%d-%m-%Y", errors="coerce", dayfirst=True)
    return pd.to_datetime(values, errors="coerce", utc=True, format="mixed", dayfirst=True)


def audit_file(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    result: dict[str, object] = {
        "file": path.relative_to(ROOT).as_posix(),
        "format": suffix or "unknown",
        "date_range": "Not a supported tabular file",
        "rows": "N/A",
        "missing": "N/A",
        "regularity": "N/A",
        "gaps": "N/A",
        "station_variables": "N/A",
    }
    if suffix not in {".csv", ".xlsx", ".xls", ".parquet"}:
        return result
    frame = _readable_tabular(path)
    result["rows"] = len(frame)
    result["missing"] = f"{frame.isna().mean().mul(100).mean():.2f}% (mean across columns)"
    station_column = next(
        (column for column in ("Site", "Station", "station_name") if column in frame),
        None,
    )
    variable_columns = [
        column
        for column in frame.columns
        if "water level" in str(column).lower()
        or "discharge" in str(column).lower()
        or "rain" in str(column).lower()
    ]
    station_names = (
        ", ".join(frame[station_column].dropna().astype(str).unique()[:20])
        if station_column
        else "station column not found"
    )
    result["station_variables"] = (
        f"stations: {station_names}; variables: {', '.join(map(str, variable_columns))}"
    )
    date_columns = _date_columns(frame)
    if not date_columns:
        result["regularity"] = "No datetime/date/time column found"
        result["gaps"] = "Cannot determine"
        return result
    dates = _parse_dates(frame[date_columns[0]], date_columns[0]).dropna().sort_values()
    if dates.empty:
        result["date_range"] = "No parseable dates"
        return result
    result["date_range"] = f"{dates.iloc[0].date()} to {dates.iloc[-1].date()}"
    unique = pd.Series(dates).drop_duplicates().sort_values()
    if len(unique) < 2:
        result["regularity"] = "Only one timestamp"
        result["gaps"] = "None detectable"
        return result
    differences = unique.diff().dropna()
    counts = Counter(differences.dt.total_seconds())
    common_seconds = max(counts, key=counts.get)
    common_hours = common_seconds / 3600
    result["regularity"] = f"Most common step: {common_hours:g} hours"
    gap_count = int(
        (differences > pd.Timedelta(int(common_seconds * 1.5), unit="s")).sum()
    )
    result["gaps"] = str(gap_count)
    return result


def main() -> int:
    files = sorted(path for path in RAW.rglob("*") if path.is_file() and path.name != ".gitkeep")
    lines = [
        "# AapdaSetu real data audit report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "This report includes real files only. It contains no synthetic observations "
        "or fabricated metrics.",
        "",
        "| File | Format | Date range | Rows | Missing value % | "
        "Time-step regularity | Gaps | Station / variable names |",
        "|---|---|---|---:|---:|---|---:|---|",
    ]
    if not files:
        lines.extend([
            "| _No real files found_ | - | - | - | - | - | - | Supply files to "
            "`ml/data/raw`; see `docs/data_inventory.md` |",
            "",
        ])
    else:
        for path in files:
            try:
                audit = audit_file(path)
                lines.append(
                    "| {file} | {format} | {date_range} | {rows} | {missing} | "
                    "{regularity} | {gaps} | {station_variables} |".format(**audit)
                )
            except Exception as error:
                lines.append(
                    f"| {path.relative_to(ROOT).as_posix()} | "
                    f"{path.suffix or 'unknown'} | Audit error | - | - | - | - | "
                    f"{error} |"
                )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown audit written to {REPORT.relative_to(ROOT).as_posix()}")
    if not files:
        print("No real files found in ml/data/raw. No metrics or predictions were generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
