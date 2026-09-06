"""Profile a saved Forecasts_Hour JSON sample without fetching new data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


KEY_COLUMNS = ["HourUTC", "PriceArea", "ForecastType"]
FORECAST_COLUMNS = [
    "ForecastDayAhead",
    "ForecastIntraday",
    "Forecast5Hour",
    "Forecast1Hour",
    "ForecastCurrent",
]
EXPECTED_COLUMNS = [
    "HourUTC",
    "HourDK",
    "PriceArea",
    "ForecastType",
    *FORECAST_COLUMNS,
    "TimestampUTC",
    "TimestampDK",
]


def integer_dict(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.items()}


def profile(input_path: Path) -> dict[str, object]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError("The saved sample contains no records.")

    missing_columns = [column for column in EXPECTED_COLUMNS if column not in frame]
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")

    frame["HourUTC_parsed"] = pd.to_datetime(frame["HourUTC"], utc=True)
    frame["TimestampUTC_parsed"] = pd.to_datetime(frame["TimestampUTC"], utc=True)
    frame["current_timestamp_offset_minutes"] = (
        frame["TimestampUTC_parsed"] - frame["HourUTC_parsed"]
    ).dt.total_seconds() / 60

    duplicate_mask = frame.duplicated(KEY_COLUMNS, keep=False)
    pair_present = frame["Forecast5Hour"].notna() & frame["Forecast1Hour"].notna()
    pair_positive = (frame["Forecast5Hour"] > 0) & (frame["Forecast1Hour"] > 0)

    zero_counts_by_type: dict[str, dict[str, int]] = {}
    pairing_by_type: dict[str, dict[str, int]] = {}
    timestamp_position_by_type: dict[str, dict[str, int]] = {}
    for forecast_type, group in frame.groupby("ForecastType", sort=True):
        zero_counts_by_type[str(forecast_type)] = {
            column: int((group[column] == 0).sum()) for column in FORECAST_COLUMNS
        }
        group_pair_present = pair_present.loc[group.index]
        group_pair_positive = pair_positive.loc[group.index]
        pairing_by_type[str(forecast_type)] = {
            "rows": int(len(group)),
            "5h_and_1h_non_null": int(group_pair_present.sum()),
            "5h_and_1h_both_positive": int(group_pair_positive.sum()),
            "5h_or_1h_zero": int(
                ((group["Forecast5Hour"] == 0) | (group["Forecast1Hour"] == 0)).sum()
            ),
        }
        offsets = group["current_timestamp_offset_minutes"]
        timestamp_position_by_type[str(forecast_type)] = {
            "timestamp_before_delivery_start": int((offsets < 0).sum()),
            "timestamp_at_or_after_delivery_start": int((offsets >= 0).sum()),
        }

    return {
        "source_file": str(input_path),
        "api_reported_total": int(payload.get("total", len(frame))),
        "records_returned": int(len(frame)),
        "columns": list(records[0]),
        "expected_columns_present": True,
        "hour_utc_min": frame["HourUTC"].min(),
        "hour_utc_max": frame["HourUTC"].max(),
        "distinct_delivery_hours": int(frame["HourUTC"].nunique()),
        "price_area_counts": integer_dict(frame["PriceArea"].value_counts().sort_index()),
        "forecast_type_counts": integer_dict(
            frame["ForecastType"].value_counts().sort_index()
        ),
        "official_primary_key": KEY_COLUMNS,
        "unique_primary_keys": int(frame[KEY_COLUMNS].drop_duplicates().shape[0]),
        "duplicate_primary_key_rows": int(duplicate_mask.sum()),
        "null_counts": {
            column: int(frame[column].isna().sum()) for column in EXPECTED_COLUMNS
        },
        "zero_counts_by_forecast_type": zero_counts_by_type,
        "5h_to_1h_pairing_by_forecast_type": pairing_by_type,
        "current_timestamp_position_by_forecast_type": timestamp_position_by_type,
        "interpretation_limits": [
            "A non-null or positive value does not prove point-in-time eligibility.",
            "TimestampUTC describes ForecastCurrent, not Forecast1Hour or Forecast5Hour.",
            "A one-day sample cannot establish development-period coverage.",
            "Zero and missing must not be treated as equivalent without evidence.",
        ],
    }


def render_markdown(result: dict[str, object]) -> str:
    lines = [
        "# Forecasts_Hour One-Day Sample Profile",
        "",
        "## Scope",
        "",
        f"- Source file: `{result['source_file']}`",
        f"- UTC coverage: `{result['hour_utc_min']}` to `{result['hour_utc_max']}`",
        f"- Records: `{result['records_returned']}`",
        f"- Distinct delivery hours: `{result['distinct_delivery_hours']}`",
        "",
        "## Row Grain and Key",
        "",
        f"- Official primary key: `{', '.join(result['official_primary_key'])}`",
        f"- Unique keys: `{result['unique_primary_keys']}`",
        f"- Rows involved in duplicate keys: `{result['duplicate_primary_key_rows']}`",
        "",
        "## Forecast Types and Pairing",
        "",
        "| Forecast type | Rows | 5h and 1h non-null | Both positive | 5h or 1h zero |",
        "|---|---:|---:|---:|---:|",
    ]
    for forecast_type, values in result["5h_to_1h_pairing_by_forecast_type"].items():
        lines.append(
            f"| {forecast_type} | {values['rows']} | "
            f"{values['5h_and_1h_non_null']} | "
            f"{values['5h_and_1h_both_positive']} | "
            f"{values['5h_or_1h_zero']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Limits",
            "",
            *[f"- {item}" for item in result["interpretation_limits"]],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("json_output", type=Path)
    parser.add_argument("markdown_output", type=Path)
    args = parser.parse_args()

    result = profile(args.input)
    args.json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
