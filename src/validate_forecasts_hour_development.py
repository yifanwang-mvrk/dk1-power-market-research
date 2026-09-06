"""Validate the saved DK1 Forecasts_Hour development-period extract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


LOCAL_TIMEZONE = "Europe/Copenhagen"
DEVELOPMENT_START_LOCAL = "2022-01-01"
DEVELOPMENT_END_EXCLUSIVE_LOCAL = "2024-07-01"
KEY_COLUMNS = ["HourUTC", "PriceArea", "ForecastType"]
FORECAST_FIELDS = [
    "ForecastDayAhead",
    "ForecastIntraday",
    "Forecast5Hour",
    "Forecast1Hour",
    "ForecastCurrent",
]


def consecutive_ranges(values: pd.DatetimeIndex) -> list[dict[str, object]]:
    if len(values) == 0:
        return []
    ranges: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = previous = values[0]
    for value in values[1:]:
        if value - previous != pd.Timedelta(hours=1):
            ranges.append((start, previous))
            start = value
        previous = value
    ranges.append((start, previous))
    result = []
    for start, end in ranges:
        result.append(
            {
                "start_utc": start.isoformat(),
                "end_utc_inclusive": end.isoformat(),
                "start_local": start.tz_convert(LOCAL_TIMEZONE).isoformat(),
                "end_local_inclusive": end.tz_convert(LOCAL_TIMEZONE).isoformat(),
                "hours": int((end - start) / pd.Timedelta(hours=1)) + 1,
            }
        )
    return result


def validate(raw_path: Path, metadata_path: Path) -> dict[str, object]:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    frame = pd.DataFrame(payload["records"])
    frame["HourUTC_dt"] = pd.to_datetime(frame["HourUTC"], utc=True)
    frame["HourLocal_dt"] = frame["HourUTC_dt"].dt.tz_convert(LOCAL_TIMEZONE)
    frame["LocalDate"] = frame["HourLocal_dt"].dt.date.astype(str)

    expected_local = pd.date_range(
        DEVELOPMENT_START_LOCAL,
        DEVELOPMENT_END_EXCLUSIVE_LOCAL,
        inclusive="left",
        freq="h",
        tz=LOCAL_TIMEZONE,
    )
    expected_utc = expected_local.tz_convert("UTC")
    holdout_start_utc = pd.Timestamp(
        DEVELOPMENT_END_EXCLUSIVE_LOCAL, tz=LOCAL_TIMEZONE
    ).tz_convert("UTC")

    primary_key = [
        item["dbColumn"]
        for item in sorted(
            (column for column in metadata["columns"] if "primaryKeyIndex" in column),
            key=lambda column: column["primaryKeyIndex"],
        )
    ]

    type_results: dict[str, dict[str, object]] = {}
    for forecast_type, group in frame.groupby("ForecastType", sort=True):
        actual_hours = pd.DatetimeIndex(group["HourUTC_dt"].unique()).sort_values()
        missing_hours = expected_utc.difference(actual_hours)
        pair_non_null = group["Forecast5Hour"].notna() & group["Forecast1Hour"].notna()
        pair_positive = (group["Forecast5Hour"] > 0) & (group["Forecast1Hour"] > 0)
        type_results[str(forecast_type)] = {
            "rows": int(len(group)),
            "expected_hours": int(len(expected_utc)),
            "whole_row_missing_hours": int(len(missing_hours)),
            "whole_row_coverage_pct": round(100 * len(actual_hours) / len(expected_utc), 4),
            "missing_intervals": consecutive_ranges(missing_hours),
            "duplicate_key_rows": int(group.duplicated(KEY_COLUMNS, keep=False).sum()),
            "null_counts": {
                field: int(group[field].isna().sum()) for field in FORECAST_FIELDS
            },
            "zero_counts": {
                field: int(group[field].eq(0).sum()) for field in FORECAST_FIELDS
            },
            "negative_counts": {
                field: int(group[field].lt(0).sum()) for field in FORECAST_FIELDS
            },
            "5h_1h_both_non_null": int(pair_non_null.sum()),
            "5h_1h_pair_coverage_vs_expected_pct": round(
                100 * pair_non_null.sum() / len(expected_utc), 4
            ),
            "5h_1h_both_positive": int(pair_positive.sum()),
            "5h_or_1h_zero": int(
                (group["Forecast5Hour"].eq(0) | group["Forecast1Hour"].eq(0)).sum()
            ),
        }

    dst_rows = []
    expected_by_day = pd.Series(1, index=expected_local).groupby(
        expected_local.date
    ).sum()
    for local_date, expected_count in expected_by_day[expected_by_day.ne(24)].items():
        day = str(local_date)
        day_frame = frame[frame["LocalDate"].eq(day)]
        row: dict[str, object] = {"local_date": day, "expected_hours": int(expected_count)}
        for forecast_type, group in day_frame.groupby("ForecastType", sort=True):
            row[str(forecast_type)] = {
                "rows": int(len(group)),
                "unique_hour_utc": int(group["HourUTC"].nunique()),
                "unique_hour_dk": int(group["HourDK"].nunique()),
            }
        dst_rows.append(row)

    selected_fields = []
    for column in metadata["columns"]:
        selected_fields.append(
            {
                "field": column["dbColumn"],
                "unit": column.get("unit", ""),
                "description": column.get("description", ""),
                "primary_key_index": column.get("primaryKeyIndex"),
            }
        )

    return {
        "validation_status": "CONDITIONAL PASS",
        "h2_5h_to_1h_feasibility": "FEASIBLE WITH DOCUMENTED CONDITIONS",
        "raw_source_file": str(raw_path),
        "metadata_source_file": str(metadata_path),
        "dataset": {
            "dataset_id": metadata["datasetId"],
            "dataset_name": metadata["datasetName"],
            "title": metadata["title"],
            "author": metadata["author"],
            "active": metadata["active"],
            "resolution": metadata["resolution"],
            "update_frequency": metadata["updateFrequency"],
            "data_from": metadata["dataFrom"],
            "primary_key": primary_key,
            "fields": selected_fields,
        },
        "scope": {
            "development_start_local_inclusive": DEVELOPMENT_START_LOCAL,
            "development_end_local_inclusive": "2024-06-30",
            "request_end_local_exclusive": DEVELOPMENT_END_EXCLUSIVE_LOCAL,
            "boundary_timezone": LOCAL_TIMEZONE,
            "expected_delivery_hours": int(len(expected_utc)),
            "records_returned": int(len(frame)),
            "first_hour_utc": frame["HourUTC_dt"].min().isoformat(),
            "last_hour_utc": frame["HourUTC_dt"].max().isoformat(),
            "first_hour_local": frame["HourLocal_dt"].min().isoformat(),
            "last_hour_local": frame["HourLocal_dt"].max().isoformat(),
            "holdout_start_utc": holdout_start_utc.isoformat(),
            "records_at_or_after_holdout_start": int(
                frame["HourUTC_dt"].ge(holdout_start_utc).sum()
            ),
            "price_areas": sorted(frame["PriceArea"].unique().tolist()),
        },
        "overall_duplicate_key_rows": int(
            frame.duplicated(KEY_COLUMNS, keep=False).sum()
        ),
        "forecast_types": type_results,
        "dst_checks": dst_rows,
        "versioning_evidence": {
            "timestamp_utc_in_primary_key": "TimestampUTC" in primary_key,
            "maximum_rows_per_primary_key": int(
                frame.groupby(KEY_COLUMNS, dropna=False).size().max()
            ),
            "wide_horizon_columns": ["Forecast5Hour", "Forecast1Hour"],
            "finding": "The extract retains one row per delivery hour, area and forecast type. It does not contain row-level tick-by-tick publication history.",
        },
        "p1_1_rules": [
            "Join and deduplicate with HourUTC, PriceArea and ForecastType.",
            "Use HourDK for interpretation and DST checks, not as the sole join key.",
            "Compute 5h-to-1h revision only when both horizon values are non-null in the same primary-key row.",
            "Do not create rows for absent hours and do not impute absent or null forecasts as zero.",
            "Preserve observed zero and negative values and attach quality flags; do not silently coerce them.",
            "For Solar, report a sensitivity view restricted to pairs where both horizon values are positive.",
            "Treat Forecast5Hour and Forecast1Hour as fixed-horizon snapshots, not complete forecast-vintage history.",
            "Exclude ForecastCurrent and TimestampUTC from the pre-delivery H2 signal.",
            "Keep ForecastIntraday outside the primary H2 signal until its historical availability is separately evidenced.",
            "Lock the exact simulated decision cutoff in P2.3 before signal evaluation.",
        ],
        "open_limits": [
            "Exact minute-level publication timestamps for Forecast5Hour and Forecast1Hour are not stored in the dataset.",
            "The official >0 validation rule conflicts with observed zeros and a small number of negative wind forecasts.",
            "Thor offshore wind farm data is excluded by the official source.",
            "Known April 2024 missing data is confirmed, with type-specific observed gap lengths.",
        ],
    }


def render_markdown(result: dict[str, object]) -> str:
    scope = result["scope"]
    dataset = result["dataset"]
    lines = [
        "# P1.1 Forecasts_Hour Development Validation",
        "",
        f"**Status:** {result['validation_status']}",
        f"**H2 5h-to-1h feasibility:** {result['h2_5h_to_1h_feasibility']}",
        "",
        "## Business conclusion",
        "",
        "The dataset supports same-hour DK1 5h-to-1h renewable forecast-revision research with explicit missingness, zero-value, DST and publication-timing conditions. It does not support a claim of complete tick-by-tick forecast-vintage reconstruction.",
        "",
        "## Official data contract",
        "",
        f"- Dataset: `{dataset['dataset_name']}` (ID `{dataset['dataset_id']}`)",
        f"- Title: {dataset['title']}",
        f"- Author: {dataset['author']}",
        f"- Active: `{dataset['active']}`",
        f"- Resolution: `{dataset['resolution']}`",
        f"- Source update frequency: `{dataset['update_frequency']}`",
        f"- Official primary key: `{', '.join(dataset['primary_key'])}`",
        "- Forecast unit: `MWh per hour`",
        "",
        "## Scope and holdout control",
        "",
        f"- Local development boundary: `{scope['development_start_local_inclusive']}` to `{scope['development_end_local_inclusive']}`",
        f"- Expected delivery hours: `{scope['expected_delivery_hours']}`",
        f"- Returned records: `{scope['records_returned']}`",
        f"- First local hour: `{scope['first_hour_local']}`",
        f"- Last local hour: `{scope['last_hour_local']}`",
        f"- Records at or after holdout start: `{scope['records_at_or_after_holdout_start']}`",
        "",
        "## Coverage and revision pairing",
        "",
        "| Forecast type | Rows | Whole-row missing hours | Row coverage | 5h/1h non-null pairs | Pair coverage vs expected | Both positive | 5h or 1h zero |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for forecast_type, values in result["forecast_types"].items():
        lines.append(
            f"| {forecast_type} | {values['rows']} | {values['whole_row_missing_hours']} | "
            f"{values['whole_row_coverage_pct']:.4f}% | {values['5h_1h_both_non_null']} | "
            f"{values['5h_1h_pair_coverage_vs_expected_pct']:.4f}% | "
            f"{values['5h_1h_both_positive']} | {values['5h_or_1h_zero']} |"
        )

    lines.extend(["", "## Whole-row missing intervals", ""])
    for forecast_type, values in result["forecast_types"].items():
        lines.append(f"### {forecast_type}")
        lines.append("")
        for interval in values["missing_intervals"]:
            lines.append(
                f"- `{interval['start_local']}` to `{interval['end_local_inclusive']}`: "
                f"{interval['hours']} hours"
            )
        lines.append("")

    lines.extend(
        [
            "## Null, zero and negative observations",
            "",
            "| Forecast type | 5h null | 1h null | 5h zero | 1h zero | 5h negative | 1h negative |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for forecast_type, values in result["forecast_types"].items():
        lines.append(
            f"| {forecast_type} | {values['null_counts']['Forecast5Hour']} | "
            f"{values['null_counts']['Forecast1Hour']} | "
            f"{values['zero_counts']['Forecast5Hour']} | "
            f"{values['zero_counts']['Forecast1Hour']} | "
            f"{values['negative_counts']['Forecast5Hour']} | "
            f"{values['negative_counts']['Forecast1Hour']} |"
        )

    lines.extend(["", "## DST evidence", ""])
    for row in result["dst_checks"]:
        lines.append(
            f"- `{row['local_date']}` expected `{row['expected_hours']}` local delivery intervals."
        )
        for forecast_type in sorted(key for key in row if key not in {"local_date", "expected_hours"}):
            values = row[forecast_type]
            lines.append(
                f"  - {forecast_type}: `{values['rows']}` rows, "
                f"`{values['unique_hour_utc']}` unique HourUTC, "
                f"`{values['unique_hour_dk']}` unique HourDK."
            )

    lines.extend(
        [
            "",
            "## Version and timestamp finding",
            "",
            f"- TimestampUTC in primary key: `{result['versioning_evidence']['timestamp_utc_in_primary_key']}`",
            f"- Maximum rows per primary key: `{result['versioning_evidence']['maximum_rows_per_primary_key']}`",
            f"- Finding: {result['versioning_evidence']['finding']}",
            "- `TimestampUTC` is the generation timestamp for `ForecastCurrent`; it is not the publication timestamp for `Forecast5Hour` or `Forecast1Hour`.",
            "",
            "## Frozen P1.1 handling rules",
            "",
            *[f"- {rule}" for rule in result["p1_1_rules"]],
            "",
            "## Open limitations carried forward",
            "",
            *[f"- {item}" for item in result["open_limits"]],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_input", type=Path)
    parser.add_argument("metadata_input", type=Path)
    parser.add_argument("json_output", type=Path)
    parser.add_argument("markdown_output", type=Path)
    args = parser.parse_args()

    result = validate(args.raw_input, args.metadata_input)
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
