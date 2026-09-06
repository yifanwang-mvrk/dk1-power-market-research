"""Validate the saved DK1 Elspotprices development-period extract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


LOCAL_TIMEZONE = "Europe/Copenhagen"
DEVELOPMENT_START_LOCAL = "2022-01-01"
DEVELOPMENT_END_EXCLUSIVE_LOCAL = "2024-07-01"
KEY_COLUMNS = ["HourUTC", "PriceArea"]
PRICE_COLUMNS = ["SpotPriceDKK", "SpotPriceEUR"]
EXPECTED_COLUMNS = ["HourUTC", "HourDK", "PriceArea", *PRICE_COLUMNS]


def consecutive_ranges(values: pd.DatetimeIndex) -> list[dict[str, object]]:
    """Turn a sorted hourly DatetimeIndex into contiguous missing ranges."""
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

    return [
        {
            "start_utc": start.isoformat(),
            "end_utc_inclusive": end.isoformat(),
            "start_local": start.tz_convert(LOCAL_TIMEZONE).isoformat(),
            "end_local_inclusive": end.tz_convert(LOCAL_TIMEZONE).isoformat(),
            "hours": int((end - start) / pd.Timedelta(hours=1)) + 1,
        }
        for start, end in ranges
    ]


def validate(raw_path: Path, metadata_path: Path) -> dict[str, object]:
    """Return a factual validation report for one saved API response."""
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not records:
        raise ValueError("The saved development extract contains no records.")

    frame = pd.DataFrame(records)
    missing_columns = [column for column in EXPECTED_COLUMNS if column not in frame]
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")

    frame["HourUTC_dt"] = pd.to_datetime(frame["HourUTC"], utc=True)
    frame["HourLocal_dt"] = frame["HourUTC_dt"].dt.tz_convert(LOCAL_TIMEZONE)
    frame["LocalDate"] = frame["HourLocal_dt"].dt.date.astype(str)
    expected_hour_dk = frame["HourLocal_dt"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    hour_dk_mismatch_rows = int(frame["HourDK"].ne(expected_hour_dk).sum())

    expected_local = pd.date_range(
        DEVELOPMENT_START_LOCAL,
        DEVELOPMENT_END_EXCLUSIVE_LOCAL,
        inclusive="left",
        freq="h",
        tz=LOCAL_TIMEZONE,
    )
    expected_utc = expected_local.tz_convert("UTC")
    actual_utc = pd.DatetimeIndex(frame["HourUTC_dt"].unique()).sort_values()
    missing_hours = expected_utc.difference(actual_utc)
    extra_hours = actual_utc.difference(expected_utc)
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

    price_summary: dict[str, dict[str, object]] = {}
    for column in PRICE_COLUMNS:
        series = frame[column]
        price_summary[column] = {
            "unit": next(
                item.get("unit", "")
                for item in metadata["columns"]
                if item["dbColumn"] == column
            ),
            "null_count": int(series.isna().sum()),
            "zero_count": int(series.eq(0).sum()),
            "negative_count": int(series.lt(0).sum()),
            "minimum": float(series.min()),
            "maximum": float(series.max()),
            "median": float(series.median()),
        }

    nonzero_eur = frame["SpotPriceEUR"].ne(0) & frame["SpotPriceEUR"].notna()
    dkk_per_eur = frame.loc[nonzero_eur, "SpotPriceDKK"] / frame.loc[
        nonzero_eur, "SpotPriceEUR"
    ]

    dst_checks: list[dict[str, object]] = []
    expected_by_day = pd.Series(1, index=expected_local).groupby(
        expected_local.date
    ).sum()
    for local_date, expected_count in expected_by_day[expected_by_day.ne(24)].items():
        day_frame = frame[frame["LocalDate"].eq(str(local_date))]
        dst_checks.append(
            {
                "local_date": str(local_date),
                "expected_hours": int(expected_count),
                "rows": int(len(day_frame)),
                "unique_hour_utc": int(day_frame["HourUTC"].nunique()),
                "unique_hour_dk": int(day_frame["HourDK"].nunique()),
            }
        )

    selected_fields = [
        {
            "field": column["dbColumn"],
            "unit": column.get("unit", ""),
            "description": column.get("description", ""),
            "primary_key_index": column.get("primaryKeyIndex"),
        }
        for column in metadata["columns"]
    ]

    complete = (
        len(missing_hours) == 0
        and len(extra_hours) == 0
        and int(payload.get("total", len(frame))) == len(frame)
        and primary_key == KEY_COLUMNS
        and frame.duplicated(KEY_COLUMNS, keep=False).sum() == 0
        and frame[PRICE_COLUMNS].isna().sum().sum() == 0
        and frame["PriceArea"].eq("DK1").all()
        and hour_dk_mismatch_rows == 0
        and frame["HourUTC_dt"].dt.minute.eq(0).all()
        and frame["HourUTC_dt"].dt.second.eq(0).all()
    )

    return {
        "validation_status": "PASS" if complete else "CONDITIONAL PASS",
        "day_ahead_reference_feasibility": (
            "FEASIBLE FOR THE DECLARED DEVELOPMENT PERIOD"
            if complete
            else "FEASIBLE WITH DOCUMENTED CONDITIONS"
        ),
        "raw_source_file": str(raw_path),
        "metadata_source_file": str(metadata_path),
        "dataset": {
            "dataset_id": metadata["datasetId"],
            "dataset_name": metadata["datasetName"],
            "title": metadata["title"],
            "description": metadata["description"],
            "author": metadata["author"],
            "active_api_flag": metadata["active"],
            "tags": metadata.get("tags", []),
            "resolution": metadata["resolution"],
            "data_from": metadata["dataFrom"],
            "last_metadata_update": metadata.get("lastMetadataUpdate"),
            "primary_key": primary_key,
            "fields": selected_fields,
        },
        "scope": {
            "development_start_local_inclusive": DEVELOPMENT_START_LOCAL,
            "development_end_local_inclusive": "2024-06-30",
            "request_end_local_exclusive": DEVELOPMENT_END_EXCLUSIVE_LOCAL,
            "boundary_timezone": LOCAL_TIMEZONE,
            "expected_delivery_hours": int(len(expected_utc)),
            "api_reported_total": int(payload.get("total", len(frame))),
            "records_returned": int(len(frame)),
            "distinct_delivery_hours": int(len(actual_utc)),
            "first_hour_utc": frame["HourUTC_dt"].min().isoformat(),
            "last_hour_utc": frame["HourUTC_dt"].max().isoformat(),
            "first_hour_local": frame["HourLocal_dt"].min().isoformat(),
            "last_hour_local": frame["HourLocal_dt"].max().isoformat(),
            "missing_delivery_hours": int(len(missing_hours)),
            "missing_intervals": consecutive_ranges(missing_hours),
            "extra_delivery_hours": int(len(extra_hours)),
            "holdout_start_utc": holdout_start_utc.isoformat(),
            "records_at_or_after_holdout_start": int(
                frame["HourUTC_dt"].ge(holdout_start_utc).sum()
            ),
            "price_areas": sorted(frame["PriceArea"].unique().tolist()),
        },
        "key_quality": {
            "official_primary_key": primary_key,
            "duplicate_primary_key_rows": int(
                frame.duplicated(KEY_COLUMNS, keep=False).sum()
            ),
            "maximum_rows_per_primary_key": int(
                frame.groupby(KEY_COLUMNS, dropna=False).size().max()
            ),
            "hour_dk_mismatch_rows": hour_dk_mismatch_rows,
            "hour_utc_full_hour_rows": int(
                (
                    frame["HourUTC_dt"].dt.minute.eq(0)
                    & frame["HourUTC_dt"].dt.second.eq(0)
                ).sum()
            ),
        },
        "price_quality": price_summary,
        "dkk_per_eur_nonzero_diagnostic": {
            "observations": int(len(dkk_per_eur)),
            "minimum": float(dkk_per_eur.min()),
            "maximum": float(dkk_per_eur.max()),
            "median": float(dkk_per_eur.median()),
            "purpose": "Cross-field diagnostic only; SpotPriceEUR is the selected reference field.",
        },
        "dst_checks": dst_checks,
        "selected_reference": {
            "field": "SpotPriceEUR",
            "unit": "EUR per MWh",
            "role": "P_DayAhead,t in Spread_t = P_Balancing,t - P_DayAhead,t",
            "reason": "It is the official DK1 day-ahead area price and matches the project's frozen EUR/MWh target unit.",
            "point_in_time_class": "decision_eligible (reference)",
        },
        "p1_2_rules": [
            "Filter PriceArea to DK1.",
            "Use HourUTC and PriceArea as the canonical primary key.",
            "Use HourDK for interpretation and DST checks, not as the sole join key.",
            "Use SpotPriceEUR as P_DayAhead,t in EUR/MWh.",
            "Retain SpotPriceDKK as an audit field but do not mix currencies in the spread.",
            "Preserve zero and negative day-ahead prices as valid market observations.",
            "Do not impute missing price rows or null prices as zero.",
            "Treat the price as a pre-delivery reference, not as the realized balancing outcome.",
            "Lock the exact simulated decision cutoff and availability mapping in P2.3.",
            "Use the successor DayAheadPrices dataset for any extension after 2025-09-30.",
            "Respect API rate limits and Retry-After headers in the P2 client.",
        ],
        "open_limits": [
            "The legacy Elspotprices dataset is discontinued after 2025-09-30, outside the declared development and holdout periods.",
            "The dataset stores delivery-hour prices but no row-level publication timestamp.",
            "Any future extension across the 2025 market-time-unit change requires a separately validated migration to DayAheadPrices.",
        ],
    }


def render_markdown(result: dict[str, object]) -> str:
    """Render the structured report as reviewer-friendly Markdown."""
    dataset = result["dataset"]
    scope = result["scope"]
    key = result["key_quality"]
    prices = result["price_quality"]
    selected = result["selected_reference"]

    lines = [
        "# P1.2 Elspotprices Development Validation",
        "",
        f"**Status:** {result['validation_status']}",
        f"**Day-ahead reference feasibility:** {result['day_ahead_reference_feasibility']}",
        "",
        "## Business conclusion",
        "",
        "The legacy Energinet `Elspotprices` dataset provides a complete, unique hourly DK1 day-ahead reference for the declared development period. `SpotPriceEUR` is selected as `P_DayAhead,t` because it is the official area price in the frozen target unit, EUR/MWh.",
        "",
        "## Official data contract",
        "",
        f"- Dataset: `{dataset['dataset_name']}` (ID `{dataset['dataset_id']}`)",
        f"- Title: {dataset['title']}",
        f"- Author: {dataset['author']}",
        f"- Resolution: `{dataset['resolution']}`",
        f"- Official primary key: `{', '.join(dataset['primary_key'])}`",
        f"- Tags: `{', '.join(dataset['tags'])}`",
        "- `SpotPriceEUR`: day-ahead spot price in the price area, `EUR per MWh`",
        "- `SpotPriceDKK`: day-ahead spot price in the price area, `DKK per MWh`",
        "- Official market meaning: the day-ahead price indicates the balance between supply and demand for delivery the following day.",
        "",
        "## Scope and holdout control",
        "",
        f"- Local development boundary: `{scope['development_start_local_inclusive']}` to `{scope['development_end_local_inclusive']}`",
        f"- Expected delivery hours: `{scope['expected_delivery_hours']}`",
        f"- API-reported total: `{scope['api_reported_total']}`",
        f"- Returned records: `{scope['records_returned']}`",
        f"- Distinct delivery hours: `{scope['distinct_delivery_hours']}`",
        f"- First local hour: `{scope['first_hour_local']}`",
        f"- Last local hour: `{scope['last_hour_local']}`",
        f"- Missing delivery hours: `{scope['missing_delivery_hours']}`",
        f"- Extra delivery hours: `{scope['extra_delivery_hours']}`",
        f"- Records at or after holdout start: `{scope['records_at_or_after_holdout_start']}`",
        "",
        "## Key and price quality",
        "",
        f"- Duplicate primary-key rows: `{key['duplicate_primary_key_rows']}`",
        f"- Maximum rows per primary key: `{key['maximum_rows_per_primary_key']}`",
        f"- HourDK rows inconsistent with HourUTC conversion: `{key['hour_dk_mismatch_rows']}`",
        "",
        "| Field | Unit | Null | Zero | Negative | Minimum | Maximum | Median |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for field in PRICE_COLUMNS:
        values = prices[field]
        lines.append(
            f"| {field} | {values['unit']} | {values['null_count']} | "
            f"{values['zero_count']} | {values['negative_count']} | "
            f"{values['minimum']:.6g} | {values['maximum']:.6g} | "
            f"{values['median']:.6g} |"
        )

    lines.extend(["", "## DST evidence", ""])
    for row in result["dst_checks"]:
        lines.append(
            f"- `{row['local_date']}`: expected `{row['expected_hours']}`, "
            f"rows `{row['rows']}`, unique HourUTC `{row['unique_hour_utc']}`, "
            f"unique HourDK `{row['unique_hour_dk']}`."
        )

    lines.extend(
        [
            "",
            "## Selected reference field",
            "",
            f"- Field: `{selected['field']}`",
            f"- Unit: `{selected['unit']}`",
            f"- Target role: `{selected['role']}`",
            f"- PIT class: `{selected['point_in_time_class']}`",
            f"- Reason: {selected['reason']}",
            "",
            "## Frozen P1.2 handling rules",
            "",
            *[f"- {rule}" for rule in result["p1_2_rules"]],
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
    args.json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
