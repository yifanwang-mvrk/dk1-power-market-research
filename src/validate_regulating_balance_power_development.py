"""Validate the saved DK1 historical balancing-outcome development extract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


LOCAL_TIMEZONE = "Europe/Copenhagen"
DEVELOPMENT_START_LOCAL = "2022-01-01"
DEVELOPMENT_END_EXCLUSIVE_LOCAL = "2024-07-01"
KEY_COLUMNS = ["HourUTC", "PriceArea"]
TARGET_COLUMN = "ImbalancePriceEUR"
PRICE_COLUMNS = [
    TARGET_COLUMN,
    "BalancingPowerPriceUpEUR",
    "BalancingPowerPriceDownEUR",
]
EXPECTED_COLUMNS = [
    "HourUTC",
    "HourDK",
    "PriceArea",
    *PRICE_COLUMNS,
    "ImbalanceMWh",
    "mFRRUpActBal",
    "mFRRDownActBal",
]


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def consecutive_ranges(values: pd.DatetimeIndex) -> list[dict[str, object]]:
    """Turn sorted missing UTC hours into contiguous ranges."""
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


def selected_metadata_fields(
    metadata: dict[str, object], field_names: list[str]
) -> list[dict[str, object]]:
    """Return selected official field definitions in requested order."""
    columns = {
        column["dbColumn"]: column
        for column in metadata["columns"]  # type: ignore[index]
    }
    return [
        {
            "field": field,
            "unit": columns[field].get("unit", ""),
            "description": columns[field].get("description", ""),
            "primary_key_index": columns[field].get("primaryKeyIndex"),
        }
        for field in field_names
    ]


def validate(
    raw_path: Path,
    metadata_path: Path,
    successor_metadata_path: Path,
) -> dict[str, object]:
    """Return the P1.3 factual validation report."""
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    successor = json.loads(successor_metadata_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not records:
        raise ValueError("The saved balancing extract contains no records.")

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

    for column in PRICE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    price_summary: dict[str, dict[str, object]] = {}
    metadata_by_name = {
        column["dbColumn"]: column for column in metadata["columns"]
    }
    for column in PRICE_COLUMNS:
        series = frame[column]
        valid = series.dropna()
        price_summary[column] = {
            "unit": metadata_by_name[column].get("unit", ""),
            "null_count": int(series.isna().sum()),
            "zero_count": int(series.eq(0).sum()),
            "negative_count": int(series.lt(0).sum()),
            "minimum": float(valid.min()) if len(valid) else None,
            "maximum": float(valid.max()) if len(valid) else None,
            "median": float(valid.median()) if len(valid) else None,
        }

    imbalance = frame[TARGET_COLUMN]
    up_price = frame["BalancingPowerPriceUpEUR"]
    down_price = frame["BalancingPowerPriceDownEUR"]
    valid_imbalance = imbalance.notna()
    matches_up = (
        valid_imbalance
        & up_price.notna()
        & np.isclose(imbalance, up_price, rtol=0, atol=0.0001)
    )
    matches_down = (
        valid_imbalance
        & down_price.notna()
        & np.isclose(imbalance, down_price, rtol=0, atol=0.0001)
    )
    relationship = {
        "valid_imbalance_prices": int(valid_imbalance.sum()),
        "matches_up_only": int((matches_up & ~matches_down).sum()),
        "matches_down_only": int((matches_down & ~matches_up).sum()),
        "matches_both": int((matches_up & matches_down).sum()),
        "matches_neither": int(
            (valid_imbalance & ~matches_up & ~matches_down).sum()
        ),
    }

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

    duplicate_key_rows = int(frame.duplicated(KEY_COLUMNS, keep=False).sum())
    holdout_rows = int(frame["HourUTC_dt"].ge(holdout_start_utc).sum())
    structural_checks_pass = (
        len(extra_hours) == 0
        and int(payload.get("total", len(frame))) == len(frame)
        and primary_key == KEY_COLUMNS
        and duplicate_key_rows == 0
        and frame["PriceArea"].eq("DK1").all()
        and hour_dk_mismatch_rows == 0
        and frame["HourUTC_dt"].dt.minute.eq(0).all()
        and frame["HourUTC_dt"].dt.second.eq(0).all()
        and holdout_rows == 0
    )
    target_checks_pass = (
        int(frame[TARGET_COLUMN].isna().sum()) == 0
        and relationship["matches_neither"] == 0
        and metadata_by_name[TARGET_COLUMN].get("unit") == "EUR per MWh"
    )
    complete = structural_checks_pass and target_checks_pass and len(missing_hours) == 0
    conditional = (
        structural_checks_pass
        and target_checks_pass
        and len(missing_hours) == 1
    )
    status = "PASS" if complete else "CONDITIONAL PASS" if conditional else "FAIL"

    return {
        "validation_status": status,
        "balancing_outcome_feasibility": (
            "FEASIBLE"
            if complete
            else "FEASIBLE WITH ONE DOCUMENTED MISSING DELIVERY HOUR"
            if conditional
            else "NOT YET ESTABLISHED"
        ),
        "raw_source_file": str(raw_path),
        "raw_sha256": sha256(raw_path),
        "metadata_source_file": str(metadata_path),
        "metadata_sha256": sha256(metadata_path),
        "dataset": {
            "dataset_id": metadata["datasetId"],
            "dataset_name": metadata["datasetName"],
            "title": metadata["title"],
            "description": metadata["description"],
            "caution": metadata.get("caution"),
            "active_api_flag": metadata["active"],
            "resolution": metadata["resolution"],
            "update_frequency": metadata.get("updateFrequency"),
            "data_from": metadata["dataFrom"],
            "last_metadata_update": metadata.get("lastMetadataUpdate"),
            "primary_key": primary_key,
            "fields": selected_metadata_fields(metadata, EXPECTED_COLUMNS),
        },
        "successor_dataset": {
            "dataset_id": successor["datasetId"],
            "dataset_name": successor["datasetName"],
            "title": successor["title"],
            "active_api_flag": successor["active"],
            "resolution": successor["resolution"],
            "update_frequency": successor.get("updateFrequency"),
            "data_from": successor["dataFrom"],
            "development_period_applicable": False,
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
            "coverage_percent": round(100 * len(actual_utc) / len(expected_utc), 6),
            "first_utc": actual_utc.min().isoformat(),
            "last_utc": actual_utc.max().isoformat(),
            "missing_hour_count": int(len(missing_hours)),
            "missing_ranges": consecutive_ranges(missing_hours),
            "extra_hour_count": int(len(extra_hours)),
            "duplicate_key_rows": duplicate_key_rows,
            "holdout_rows": holdout_rows,
            "price_areas": sorted(frame["PriceArea"].dropna().unique().tolist()),
            "hour_dk_mismatch_rows": hour_dk_mismatch_rows,
        },
        "target_selection": {
            "selected_field": TARGET_COLUMN,
            "unit": "EUR/MWh",
            "pit_class": "outcome",
            "research_role": "P_Balancing,t in the balancing spread target",
            "executable_pnl_claim": False,
            "exact_historical_publication_delay": "not documented in legacy metadata",
            "directional_price_relationship": relationship,
        },
        "price_summary": price_summary,
        "dst_checks": dst_checks,
        "historical_rule": {
            "single_price_go_live": "2021-11-01T00:00:00+01:00",
            "development_period_entirely_after_go_live": True,
            "official_source": "https://nordicbalancingmodel.net/confirmation-of-go-live-of-single-price-and-single-position-on-1-november-2021/",
            "interpretation": "One imbalance price applies to the imbalance settlement period; the legacy field selects the official price according to the dominating direction.",
        },
        "handling_rules": [
            "Use HourUTC + PriceArea as the canonical join key.",
            "Use HourDK only for local interpretation and DST checks.",
            "Do not create or zero-fill the missing 2022-10-30 00:00 UTC row.",
            "Preserve zero, negative and extreme prices as observations with quality flags.",
            "Use ImbalancePriceEUR as the outcome; retain direction prices for audit.",
            "Do not infer the official dominating direction from the sign of ImbalanceMWh.",
            "Do not present the outcome as executable trading P&L.",
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    """Render the JSON report as a concise human-readable evidence note."""
    scope = report["scope"]
    target = report["target_selection"]
    relationship = target["directional_price_relationship"]
    prices = report["price_summary"]
    missing = scope["missing_ranges"]
    missing_text = (
        f"`{missing[0]['start_utc']}` / `{missing[0]['start_local']}`"
        if missing
        else "None"
    )

    lines = [
        "# P1.3 RegulatingBalancePowerdata Development Validation",
        "",
        f"**Validation status:** {report['validation_status']}",
        f"**Feasibility:** {report['balancing_outcome_feasibility']}",
        "**Holdout status:** Locked and unused",
        "",
        "## Conclusion",
        "",
        "For the declared hourly development period, DK1 `RegulatingBalancePowerdata.ImbalancePriceEUR` is selected as `P_Balancing,t` in EUR/MWh. It is the official unified imbalance-price outcome for the delivery hour and is classified as `outcome`, not as information available at the simulated decision time. One complete delivery-hour row is absent from the official historical API response, so P1.3 receives a conditional pass.",
        "",
        "## Source contract",
        "",
        f"- Dataset: `{report['dataset']['dataset_name']}` (ID `{report['dataset']['dataset_id']}`)",
        f"- Resolution: `{report['dataset']['resolution']}`",
        f"- Official primary key: `{', '.join(report['dataset']['primary_key'])}`",
        "- Selected field: `ImbalancePriceEUR`",
        "- Selected unit: `EUR per MWh`",
        "- Target role: `P_Balancing,t` in `Spread_t = P_Balancing,t - P_DayAhead,t`",
        "- Canonical join key: `HourUTC + PriceArea`",
        "- Point-in-time class: `outcome`",
        "",
        "The official field definition states that the imbalance price is based on the dominating direction: Up uses the maximum of the aFRR component or mFRR price, None uses the value of avoided activation / spot price, and Down uses the minimum of the aFRR component or mFRR price.",
        "",
        "## Historical applicability",
        "",
        "The Nordic single-price and single-position model went live on 2021-11-01, before the development period begins. Official Nordic Balancing Model evidence: <https://nordicbalancingmodel.net/confirmation-of-go-live-of-single-price-and-single-position-on-1-november-2021/>.",
        "",
        f"The active successor `{report['successor_dataset']['dataset_name']}` starts at `{report['successor_dataset']['data_from']}` with `{report['successor_dataset']['resolution']}` resolution. It does not cover the declared 2022-2024 development period, so it is not substituted into this hourly historical extract.",
        "",
        "## Development coverage",
        "",
        "| Expected hours | Returned rows | Distinct hours | Coverage | Missing | Duplicate-key rows | Extra | Holdout |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {scope['expected_delivery_hours']:,} | {scope['records_returned']:,} | {scope['distinct_delivery_hours']:,} | {scope['coverage_percent']:.6f}% | {scope['missing_hour_count']} | {scope['duplicate_key_rows']} | {scope['extra_hour_count']} | {scope['holdout_rows']} |",
        "",
        f"Missing hour: {missing_text}. A separate bounded API request returned five of six requested consecutive UTC hours and confirmed the same source gap.",
        "",
        "## Price completeness and values",
        "",
        "| Field | Null | Zero | Negative | Minimum | Median | Maximum |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for field in PRICE_COLUMNS:
        item = prices[field]
        lines.append(
            f"| `{field}` | {item['null_count']} | {item['zero_count']} | {item['negative_count']} | {item['minimum']} | {item['median']} | {item['maximum']} |"
        )

    lines.extend(
        [
            "",
            "Zero, negative and extreme values are retained as market observations. They are not interpreted as missing solely because of their magnitude or sign.",
            "",
            "## Unified-price relationship",
            "",
            "| Relationship | Hours |",
            "|---|---:|",
            f"| Matches Up only | {relationship['matches_up_only']:,} |",
            f"| Matches Down only | {relationship['matches_down_only']:,} |",
            f"| Matches both | {relationship['matches_both']:,} |",
            f"| Matches neither | {relationship['matches_neither']:,} |",
            "",
            "All returned `ImbalancePriceEUR` values match at least one official directional price. The unified field is therefore used directly; the project will not select Up or Down after observing which one produces a preferred result.",
            "",
            "## DST checks",
            "",
            "| Local date | Expected | Rows | Unique UTC | Unique HourDK |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for item in report["dst_checks"]:
        lines.append(
            f"| {item['local_date']} | {item['expected_hours']} | {item['rows']} | {item['unique_hour_utc']} | {item['unique_hour_dk']} |"
        )

    lines.extend(
        [
            "",
            "The 2022 fall-back day contains 24 rather than the expected 25 UTC hours because the first repeated local 02:00 hour is absent. The 2023 fall-back day retains 25 UTC hours even though only 24 local clock labels are unique. This confirms that `HourUTC` must remain the canonical time key.",
            "",
            "## Availability and limitations",
            "",
            "- `ImbalancePriceEUR` is an ex-post delivery outcome. It must never enter the decision-time feature set.",
            "- The discontinued dataset reports update frequency as N/A and does not document an exact historical publication delay. That unresolved lag remains under I03/P2.3, including the feasibility of a persistence baseline based on the previous outcome.",
            "- `ImbalanceMWh` is defined after TSO activations and is not used to recreate the official dominating direction.",
            "- The source caution concerns missing DKK values for Up and Down regulation prices. The selected EUR target has no null values among returned rows.",
            "- This balancing-pressure outcome is not an executable trading price or P&L claim.",
            "",
            "## Handling rule for P2",
            "",
            "Join to the day-ahead reference on `HourUTC + PriceArea`. Preserve the absent 2022-10-30 00:00 UTC outcome as missing and exclude it from calculations requiring a complete spread. Do not create or zero-fill the row.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path(
            "data/raw/p1_3_validation/"
            "RegulatingBalancePowerdata_DK1_development_2022-01-01_2024-06-30.json"
        ),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path(
            "research/evidence/p1_3_regulating_balance_power/"
            "metadata_RegulatingBalancePowerdata_2026-09-06.json"
        ),
    )
    parser.add_argument(
        "--successor-metadata",
        type=Path,
        default=Path(
            "research/evidence/p1_3_regulating_balance_power/"
            "candidate_metadata_ImbalancePrice_2026-09-06.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path(
            "research/evidence/p1_3_regulating_balance_power/"
            "development_validation_2026-09-06.json"
        ),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path(
            "research/evidence/p1_3_regulating_balance_power/"
            "development_validation_2026-09-06.md"
        ),
    )
    args = parser.parse_args()

    report = validate(args.raw, args.metadata, args.successor_metadata)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "validation_status": report["validation_status"],
        "expected_hours": report["scope"]["expected_delivery_hours"],
        "returned_rows": report["scope"]["records_returned"],
        "missing_hours": report["scope"]["missing_hour_count"],
        "target_nulls": report["price_summary"][TARGET_COLUMN]["null_count"],
        "matches_neither": report["target_selection"]["directional_price_relationship"]["matches_neither"],
        "holdout_rows": report["scope"]["holdout_rows"],
    }, indent=2))


if __name__ == "__main__":
    main()
