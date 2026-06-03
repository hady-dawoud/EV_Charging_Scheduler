"""Clean Dundee charging session CSVs into a unified interim dataset."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

RAW_COLUMN_MAP = {
    "SDR ID": "raw_session_id",
    "Site": "station_name",
    "CP ID": "cp_id",
    "Connector Type": "connector_type",
    "Consum(kWh)": "energy_kwh",
    "Duration": "raw_duration",
    "Start": "arrival_ts",
    "End": "departure_ts",
    "Postcode": "postcode",
}

OUTPUT_COLUMNS = [
    "session_id",
    "source_year",
    "station_name",
    "station_id",
    "cp_id",
    "connector_type",
    "energy_kwh",
    "arrival_ts",
    "departure_ts",
    "session_minutes",
    "postcode",
    "date",
    "year",
    "month",
    "weekday",
    "hour",
    "quarter_hour_slot",
]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the Dundee cleaning job."""

    parser = argparse.ArgumentParser(description="Clean raw Dundee EV charging data.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw/dundee"))
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/interim/dundee_sessions_clean.csv"),
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=Path("data/interim/dundee_sessions_clean.parquet"),
    )
    return parser


def find_raw_files(input_dir: Path) -> list[Path]:
    """Return Dundee annual session CSV files in chronological filename order."""

    files = sorted(path for path in input_dir.glob("dundee_sessions*.csv") if path.is_file())
    if not files:
        raise FileNotFoundError(f"No Dundee CSV files found in {input_dir}.")
    return files


def extract_source_year(path: Path) -> int:
    """Extract the first 4-digit year from a Dundee source filename."""

    match = re.search(r"(20\d{2})", path.stem)
    if not match:
        raise ValueError(f"Could not determine source year from {path.name}.")
    return int(match.group(1))


def slugify_station_name(value: str) -> str:
    """Create a stable station slug for future joins and lookup tables."""

    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "unknown_station"


def normalize_text(series: pd.Series) -> pd.Series:
    """Trim whitespace and collapse internal spacing for text columns."""

    string_values = series.astype("string")
    return string_values.str.replace(r"\s+", " ", regex=True).str.strip()


def parse_duration_minutes(series: pd.Series) -> pd.Series:
    """Parse Dundee duration strings and return rounded session minutes."""

    duration_text = series.astype("string")
    valid_mask = duration_text.str.fullmatch(r"\d{1,3}:\d{2}:\d{2}", na=False)
    duration = pd.to_timedelta(duration_text.where(valid_mask), errors="coerce")
    return duration.dt.total_seconds().div(60).round().astype("Int64")


def compute_quarter_hour_slot(series: pd.Series) -> pd.Series:
    """Map arrival timestamps to a 15-minute slot index within the day."""

    return ((series.dt.hour * 60 + series.dt.minute) // 15).astype("Int64")


def clean_frame(frame: pd.DataFrame, source_year: int) -> pd.DataFrame:
    """Standardize a single Dundee raw frame."""

    cleaned = frame.rename(columns=RAW_COLUMN_MAP).copy()

    cleaned["source_year"] = source_year
    cleaned["station_name"] = normalize_text(cleaned["station_name"])
    cleaned["cp_id"] = normalize_text(cleaned["cp_id"])
    cleaned["connector_type"] = normalize_text(cleaned["connector_type"]).str.lower()
    cleaned["postcode"] = normalize_text(cleaned["postcode"])
    cleaned["energy_kwh"] = pd.to_numeric(cleaned["energy_kwh"], errors="coerce")
    cleaned["arrival_ts"] = pd.to_datetime(
        cleaned["arrival_ts"],
        format="%d/%m/%Y %H:%M",
        errors="coerce",
        dayfirst=True,
    )
    cleaned["departure_ts"] = pd.to_datetime(
        cleaned["departure_ts"],
        format="%d/%m/%Y %H:%M",
        errors="coerce",
        dayfirst=True,
    )

    duration_minutes = parse_duration_minutes(cleaned["raw_duration"])
    repaired_departure = cleaned["arrival_ts"] + pd.to_timedelta(duration_minutes, unit="m")
    invalid_departure_mask = cleaned["departure_ts"].isna() | cleaned["departure_ts"].lt(cleaned["arrival_ts"])
    cleaned["departure_ts"] = cleaned["departure_ts"].mask(invalid_departure_mask, repaired_departure)

    fallback_minutes = cleaned["departure_ts"].sub(cleaned["arrival_ts"]).dt.total_seconds().div(60).round()
    fallback_minutes = fallback_minutes.where(fallback_minutes >= 0).astype("Int64")
    cleaned["session_minutes"] = duration_minutes.fillna(fallback_minutes)

    cleaned["station_id"] = cleaned["station_name"].fillna("unknown_station").map(slugify_station_name)
    cleaned["session_id"] = (
        "dundee_"
        + cleaned["raw_session_id"].astype("string").str.strip().fillna("")
    )
    missing_session_mask = cleaned["session_id"].eq("dundee_")
    if missing_session_mask.any():
        cleaned.loc[missing_session_mask, "session_id"] = (
            "dundee_"
            + cleaned.loc[missing_session_mask].index.astype(str)
        )

    cleaned["date"] = cleaned["arrival_ts"].dt.date.astype("string")
    cleaned["year"] = cleaned["arrival_ts"].dt.year.astype("Int64")
    cleaned["month"] = cleaned["arrival_ts"].dt.month.astype("Int64")
    cleaned["weekday"] = cleaned["arrival_ts"].dt.day_name()
    cleaned["hour"] = cleaned["arrival_ts"].dt.hour.astype("Int64")
    cleaned["quarter_hour_slot"] = compute_quarter_hour_slot(cleaned["arrival_ts"])

    return cleaned[OUTPUT_COLUMNS]


def load_and_clean_files(paths: Iterable[Path]) -> pd.DataFrame:
    """Load all Dundee files and return one cleaned dataframe."""

    frames: list[pd.DataFrame] = []
    for path in paths:
        raw_frame = pd.read_csv(path)
        frames.append(clean_frame(raw_frame, source_year=extract_source_year(path)))

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["arrival_ts", "session_id"], kind="stable").reset_index(drop=True)
    return combined


def ensure_output_parent(paths: Iterable[Path]) -> None:
    """Create output directories if they do not exist."""

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    """Run the Dundee cleaning pipeline."""

    args = build_parser().parse_args()
    raw_files = find_raw_files(args.input_dir)
    cleaned = load_and_clean_files(raw_files)

    ensure_output_parent([args.output_csv, args.output_parquet])
    cleaned.to_csv(args.output_csv, index=False)
    cleaned.to_parquet(args.output_parquet, index=False)

    print(f"Cleaned {len(cleaned):,} Dundee sessions from {len(raw_files)} files.")
    print(f"Wrote CSV to {args.output_csv}")
    print(f"Wrote Parquet to {args.output_parquet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
