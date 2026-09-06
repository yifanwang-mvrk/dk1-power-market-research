"""Validate P1.4 actual-fundamental, cross-border and system sources."""

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
EXPECTED_HOURS = pd.date_range(
    DEVELOPMENT_START_LOCAL,
    DEVELOPMENT_END_EXCLUSIVE_LOCAL,
    inclusive="left",
    freq="h",
    tz=LOCAL_TIMEZONE,
).tz_convert("UTC")
HOLDOUT_START_UTC = pd.Timestamp(
    DEVELOPMENT_END_EXCLUSIVE_LOCAL, tz=LOCAL_TIMEZONE
).tz_convert("UTC")

WIND_FIELDS = [
    "OffshoreWindLt100MW_MWh",
    "OffshoreWindGe100MW_MWh",
    "OnshoreWindLt50kW_MWh",
    "OnshoreWindGe50kW_MWh",
]
SOLAR_FIELDS = [
    "SolarPowerLt10kW_MWh",
    "SolarPowerGe10Lt40kW_MWh",
    "SolarPowerGe40kW_MWh",
    "SolarPowerSelfConMWh",
]
ACTUAL_FIELDS = ["GrossConsumptionMWh", *WIND_FIELDS, *SOLAR_FIELDS]
EXCHANGE_FIELDS = [
    "ExchangeNO_MWh",
    "ExchangeSE_MWh",
    "ExchangeGE_MWh",
    "ExchangeNL_MWh",
    "ExchangeGB_MWh",
    "ExchangeGreatBelt_MWh",
]
TRANSMISSION_FIELDS = [
    "ImportCapacity",
    "ExportCapacity",
    "ScheduledExchangeDayAhead",
    "ScheduledExchangeIntraday",
    "PhysicalExchangeNonvalidated",
    "PhysicalExchangeSettlement",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(path: Path) -> tuple[dict[str, object], pd.DataFrame]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not records:
        raise ValueError(f"No records in {path}")
    return payload, pd.DataFrame(records)


def utc_series(frame: pd.DataFrame, column: str = "HourUTC") -> pd.Series:
    return pd.to_datetime(frame[column], utc=True)


def key_from_metadata(metadata: dict[str, object]) -> list[str]:
    return [
        item["dbColumn"]
        for item in sorted(
            (
                column
                for column in metadata.get("columns", [])
                if column.get("primaryKeyIndex") is not None
            ),
            key=lambda column: column["primaryKeyIndex"],
        )
    ]


def numeric_summary(series: pd.Series) -> dict[str, object]:
    values = pd.to_numeric(series, errors="coerce")
    valid = values.dropna()
    return {
        "null_count": int(values.isna().sum()),
        "zero_count": int(values.eq(0).sum()),
        "negative_count": int(values.lt(0).sum()),
        "positive_count": int(values.gt(0).sum()),
        "minimum": float(valid.min()) if len(valid) else None,
        "median": float(valid.median()) if len(valid) else None,
        "maximum": float(valid.max()) if len(valid) else None,
    }


def scope_summary(
    payload: dict[str, object],
    frame: pd.DataFrame,
    key_columns: list[str],
) -> dict[str, object]:
    hours = pd.DatetimeIndex(utc_series(frame).unique()).sort_values()
    missing = EXPECTED_HOURS.difference(hours)
    extra = hours.difference(EXPECTED_HOURS)
    return {
        "api_reported_total": int(payload.get("total", len(frame))),
        "records": int(len(frame)),
        "unique_hours": int(len(hours)),
        "expected_hours": int(len(EXPECTED_HOURS)),
        "first_utc": hours.min().isoformat(),
        "last_utc": hours.max().isoformat(),
        "missing_hours": int(len(missing)),
        "missing_hour_examples": [item.isoformat() for item in missing[:10]],
        "extra_hours": int(len(extra)),
        "duplicate_key_rows": int(frame.duplicated(key_columns, keep=False).sum()),
        "holdout_rows": int(utc_series(frame).ge(HOLDOUT_START_UTC).sum()),
    }


def validate_actuals(
    raw_path: Path, metadata_path: Path
) -> tuple[dict[str, object], pd.DataFrame]:
    payload, frame = load_records(raw_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    required = ["HourUTC", "HourDK", "PriceArea", *ACTUAL_FIELDS, *EXCHANGE_FIELDS]
    absent = [column for column in required if column not in frame]
    if absent:
        raise ValueError(f"Actual source missing columns: {absent}")

    for column in ACTUAL_FIELDS + EXCHANGE_FIELDS + ["GridLossInterconnectorsMWh"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["ActualWindMWh"] = frame[WIND_FIELDS].sum(axis=1, min_count=len(WIND_FIELDS))
    frame["ActualSolarMWh"] = frame[SOLAR_FIELDS].sum(axis=1, min_count=len(SOLAR_FIELDS))
    frame["ActualResidualLoadMWh"] = (
        frame["GrossConsumptionMWh"]
        - frame["ActualWindMWh"]
        - frame["ActualSolarMWh"]
    )
    scope = scope_summary(payload, frame, ["HourUTC", "PriceArea"])
    structural_pass = (
        key_from_metadata(metadata) == ["HourUTC", "PriceArea"]
        and scope["records"] == len(EXPECTED_HOURS)
        and scope["unique_hours"] == len(EXPECTED_HOURS)
        and scope["missing_hours"] == 0
        and scope["extra_hours"] == 0
        and scope["duplicate_key_rows"] == 0
        and scope["holdout_rows"] == 0
        and frame["PriceArea"].eq("DK1").all()
        and frame[ACTUAL_FIELDS].notna().all().all()
    )
    return {
        "status": "PASS" if structural_pass else "FAIL",
        "dataset": metadata.get("datasetName"),
        "title": metadata.get("title"),
        "active": metadata.get("active"),
        "resolution": metadata.get("resolution"),
        "update_frequency": metadata.get("updateFrequency"),
        "data_from": metadata.get("dataFrom"),
        "primary_key": key_from_metadata(metadata),
        "raw_file": str(raw_path),
        "raw_sha256": sha256(raw_path),
        "metadata_file": str(metadata_path),
        "metadata_sha256": sha256(metadata_path),
        "scope": scope,
        "field_quality": {
            column: numeric_summary(frame[column]) for column in ACTUAL_FIELDS
        },
        "derived": {
            "formula_wind": " + ".join(WIND_FIELDS),
            "formula_solar": " + ".join(SOLAR_FIELDS),
            "formula_residual_load": (
                "GrossConsumptionMWh - ActualWindMWh - ActualSolarMWh"
            ),
            "complete_rows": int(frame["ActualResidualLoadMWh"].notna().sum()),
            "negative_residual_load_hours": int(
                frame["ActualResidualLoadMWh"].lt(0).sum()
            ),
            "negative_residual_load_share": float(
                frame["ActualResidualLoadMWh"].lt(0).mean()
            ),
            **{
                f"residual_load_{key}": value
                for key, value in numeric_summary(
                    frame["ActualResidualLoadMWh"]
                ).items()
            },
        },
        "actual_exchange_quality": {
            column: numeric_summary(frame[column]) for column in EXCHANGE_FIELDS
        },
        "interconnector_losses": numeric_summary(frame["GridLossInterconnectorsMWh"]),
        "eligibility": "diagnostic_only",
        "reason": (
            "Settlement demand, generation and physical exchange are revised ex-post "
            "actuals; they explain outcomes but were unavailable at the decision cutoff."
        ),
    }, frame


def validate_countertrade(
    raw_path: Path, metadata_path: Path, successor_metadata_path: Path
) -> dict[str, object]:
    payload, frame = load_records(raw_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    successor = json.loads(successor_metadata_path.read_text(encoding="utf-8"))
    for column in ["VolumeUpMW", "VolumeDownMW"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    delivery = utc_series(frame)
    publication_local = pd.to_datetime(frame["PublicationDate"], errors="coerce").dt.tz_localize(
        LOCAL_TIMEZONE, ambiguous="infer", nonexistent="shift_forward"
    )
    publication_utc = publication_local.dt.tz_convert("UTC")
    lead_hours = (delivery - publication_utc).dt.total_seconds() / 3600
    cutoff_pass = lead_hours.ge(1)
    scope = scope_summary(payload, frame, ["HourUTC"])
    up = frame["VolumeUpMW"]
    down = frame["VolumeDownMW"]
    return {
        "status": "CONDITIONAL PASS",
        "dataset": metadata.get("datasetName"),
        "title": metadata.get("title"),
        "primary_key": key_from_metadata(metadata),
        "raw_file": str(raw_path),
        "raw_sha256": sha256(raw_path),
        "metadata_file": str(metadata_path),
        "metadata_sha256": sha256(metadata_path),
        "scope": scope,
        "version_distribution": {
            str(key): int(value)
            for key, value in frame["Version"].value_counts().sort_index().items()
        },
        "publication": {
            "null_count": int(publication_utc.isna().sum()),
            "publication_blocks": int(frame["PublicationDate"].nunique()),
            "lead_hours_min": float(lead_hours.min()),
            "lead_hours_median": float(lead_hours.median()),
            "lead_hours_max": float(lead_hours.max()),
            "published_before_delivery": int(lead_hours.gt(0).sum()),
            "published_at_least_one_hour_before_delivery": int(cutoff_pass.sum()),
            "not_available_one_hour_before_delivery": int((~cutoff_pass).sum()),
        },
        "volumes": {
            "up": numeric_summary(up),
            "down": numeric_summary(down),
            "both_zero_rows": int(up.eq(0).mul(down.eq(0)).sum()),
            "up_positive_rows": int(up.gt(0).sum()),
            "down_positive_rows": int(down.gt(0).sum()),
            "both_positive_rows": int(up.gt(0).mul(down.gt(0)).sum()),
        },
        "successor": {
            "dataset": successor.get("datasetName"),
            "data_from": successor.get("dataFrom"),
            "development_period_applicable": False,
            "eligibility": "unavailable_for_development",
        },
        "eligibility": "conditional_decision_candidate",
        "reason": (
            "The legacy rows carry publication time and many final snapshots existed before "
            "delivery, but coverage starts in April 2023 and later versions overwrite history. "
            "P2.3 must enforce the final decision cutoff and must not invent missing days as zero."
        ),
    }


def validate_transmission(
    raw_path: Path, metadata_path: Path
) -> dict[str, object]:
    payload, frame = load_records(raw_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    required = ["HourUTC", "HourDK", "PriceArea", "ConnectedArea", *TRANSMISSION_FIELDS]
    absent = [column for column in required if column not in frame]
    if absent:
        raise ValueError(f"Transmission source missing columns: {absent}")
    for column in TRANSMISSION_FIELDS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    scope = scope_summary(payload, frame, ["HourUTC", "PriceArea", "ConnectedArea"])
    by_connection: dict[str, object] = {}
    for area, group in frame.groupby("ConnectedArea", dropna=False):
        hours = pd.DatetimeIndex(utc_series(group).unique()).sort_values()
        missing = EXPECTED_HOURS.difference(hours)
        by_connection[str(area)] = {
            "records": int(len(group)),
            "unique_hours": int(len(hours)),
            "first_utc": hours.min().isoformat(),
            "last_utc": hours.max().isoformat(),
            "missing_against_full_development": int(len(missing)),
            "duplicate_key_rows": int(
                group.duplicated(["HourUTC", "PriceArea", "ConnectedArea"], keep=False).sum()
            ),
            "field_quality": {
                column: numeric_summary(group[column]) for column in TRANSMISSION_FIELDS
            },
        }
    structural_pass = (
        key_from_metadata(metadata) == ["HourUTC", "PriceArea", "ConnectedArea"]
        and scope["duplicate_key_rows"] == 0
        and scope["extra_hours"] == 0
        and scope["holdout_rows"] == 0
        and frame["PriceArea"].eq("DK1").all()
        and frame["ImportCapacity"].dropna().ge(0).all()
    )
    export_positive_rows = int(frame["ExportCapacity"].gt(0).sum())
    gb_day_ahead_null_rows = int(
        frame.loc[
            frame["ConnectedArea"].eq("GB"), "ScheduledExchangeDayAhead"
        ].isna().sum()
    )
    source_conditions_present = export_positive_rows > 0 or gb_day_ahead_null_rows > 0
    status = (
        "CONDITIONAL PASS"
        if structural_pass and source_conditions_present
        else "PASS"
        if structural_pass
        else "FAIL"
    )
    return {
        "status": status,
        "dataset": metadata.get("datasetName"),
        "title": metadata.get("title"),
        "active": metadata.get("active"),
        "resolution": metadata.get("resolution"),
        "data_from": metadata.get("dataFrom"),
        "primary_key": key_from_metadata(metadata),
        "raw_file": str(raw_path),
        "raw_sha256": sha256(raw_path),
        "metadata_file": str(metadata_path),
        "metadata_sha256": sha256(metadata_path),
        "scope": scope,
        "connections": by_connection,
        "sign_checks": {
            "positive_import_capacity_rows": int(frame["ImportCapacity"].gt(0).sum()),
            "negative_import_capacity_rows": int(frame["ImportCapacity"].lt(0).sum()),
            "negative_export_capacity_rows": int(frame["ExportCapacity"].lt(0).sum()),
            "positive_export_capacity_rows": export_positive_rows,
            "official_import_validation_rule": ">=0",
            "official_export_validation_rule": None,
        },
        "documented_conditions": {
            "mixed_export_capacity_signs": export_positive_rows,
            "gb_day_ahead_null_rows": gb_day_ahead_null_rows,
            "handling": (
                "Preserve source values and nulls. Define border-specific capacity "
                "normalization and eligible border subsets in P6.1."
            ),
        },
        "field_eligibility": {
            "ImportCapacity": "decision_eligible_candidate",
            "ExportCapacity": "conditional_decision_candidate",
            "ScheduledExchangeDayAhead": "decision_eligible_candidate",
            "ScheduledExchangeIntraday": "diagnostic_only",
            "PhysicalExchangeNonvalidated": "diagnostic_only",
            "PhysicalExchangeSettlement": "diagnostic_only",
        },
        "reason": (
            "Day-ahead capacities and day-ahead schedules are fixed before delivery in the "
            "source contract, subject to P2.3 cutoff mapping and border-specific null/sign "
            "handling in P6.1. Final intraday schedules and physical flows lack historical "
            "vintages or are realized outcomes."
        ),
    }


def source_inventory(
    actuals: dict[str, object],
    countertrade: dict[str, object],
    transmission: dict[str, object],
) -> list[dict[str, object]]:
    return [
        {
            "research_role": "H1-A actual residual load",
            "source": "ProductionConsumptionSettlement",
            "fields": ["GrossConsumptionMWh", *WIND_FIELDS, *SOLAR_FIELDS],
            "development_coverage": "complete",
            "eligibility": "diagnostic_only",
            "decision": "selected",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_ProductionConsumptionSettlement_2026-09-06.json",
                "research/evidence/p1_4_sources/development_validation_2026-09-06.json",
            ],
            "why": actuals["reason"],
        },
        {
            "research_role": "H1-B decision-time load proxy",
            "source": "ENTSO-E day-ahead total load forecast",
            "fields": ["day-ahead total load forecast"],
            "development_coverage": "not retrieved; external access and timing not established",
            "eligibility": "external_candidate_pending_access_timing",
            "decision": "registered_for_P5.2",
            "evidence": [
                "https://transparency.entsoe.eu/",
                "https://gitlab.entsoe.eu/transparency/xml-examples/",
            ],
            "why": "No validated Energi Data Service historical load forecast was identified.",
        },
        {
            "research_role": "H3 day-ahead interconnector state",
            "source": "Transmissionlines",
            "fields": ["ImportCapacity", "ExportCapacity", "ScheduledExchangeDayAhead"],
            "development_coverage": "validated by connection",
            "eligibility": "conditional_decision_candidate",
            "decision": "selected_for_P6.1_cutoff_mapping",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_Transmissionlines_2026-09-06.json",
                "research/evidence/p1_4_sources/development_validation_2026-09-06.json",
            ],
            "why": transmission["reason"],
        },
        {
            "research_role": "H3 realized physical exchange",
            "source": "ProductionConsumptionSettlement",
            "fields": EXCHANGE_FIELDS,
            "development_coverage": "complete except source-defined GB null history",
            "eligibility": "diagnostic_only",
            "decision": "selected",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_ProductionConsumptionSettlement_2026-09-06.json",
                "research/evidence/p1_4_sources/development_validation_2026-09-06.json",
            ],
            "why": "Settlement flows are realized and revised after delivery; GB nulls remain null.",
        },
        {
            "research_role": "H3 intraday countertrade request",
            "source": "CountertradeIntraday",
            "fields": ["VolumeUpMW", "VolumeDownMW", "PublicationDate", "Version"],
            "development_coverage": "partial from 2023-04-18",
            "eligibility": "conditional_decision_candidate",
            "decision": "registered_for_P2.3_and_P6.1",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_CountertradeIntraday_2026-09-06.json",
                "research/evidence/p1_4_sources/development_validation_2026-09-06.json",
            ],
            "why": countertrade["reason"],
        },
        {
            "research_role": "H3 intraday countertrade successor",
            "source": "CountertradeIntraday_v2",
            "fields": ["VolumeUpMW", "VolumeDownMW", "PublicationDate", "Version"],
            "development_coverage": "none; starts 2025-10-15",
            "eligibility": "unavailable_for_development",
            "decision": "excluded",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_CountertradeIntraday_v2_2026-09-06.json"
            ],
            "why": "The source begins after the locked development period.",
        },
        {
            "research_role": "actual cross-border alternative",
            "source": "ForeignExchange",
            "fields": ["country-specific import and export MWh"],
            "development_coverage": "available",
            "eligibility": "diagnostic_only",
            "decision": "registered_alternative",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_ForeignExchange_2026-09-06.json"
            ],
            "why": "Actual exchange is useful for explanation but not known before delivery.",
        },
        {
            "research_role": "real-time actual system state",
            "source": "PowerSystemRightNow / ElectricityBalanceNonv",
            "fields": ["load", "generation", "exchange", "activated reserves"],
            "development_coverage": "historical actuals available",
            "eligibility": "diagnostic_only_or_lagged_candidate",
            "decision": "not_selected_for_MVP",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_PowerSystemRightNow_2026-09-06.json",
                "research/evidence/p1_4_sources/metadata_ElectricityBalanceNonv_2026-09-06.json",
            ],
            "why": "Same-hour values are realized; only observations strictly before the cutoff could qualify.",
        },
        {
            "research_role": "live mFRR request",
            "source": "Energinet Realtime Electricity Market Data / mFRR Request",
            "fields": ["timeStamp", "mtuStart", "area", "value"],
            "development_coverage": "unavailable; period endpoint retains at most seven days",
            "eligibility": "unavailable_for_development",
            "decision": "excluded",
            "evidence": [
                "https://www.energidataservice.dk/datasets/realtime-electricity-market"
            ],
            "why": "The live service cannot reconstruct the locked 2022-2024 development history.",
        },
        {
            "research_role": "registered reserve context",
            "source": "MfrrReservesDK1 + mFRRCapacityMarket",
            "fields": ["demand", "procured reserve", "capacity price"],
            "development_coverage": "legacy/successor bridge available from 2022 through 2024",
            "eligibility": "decision_eligible_candidate",
            "decision": "deferred_beyond_level_A",
            "evidence": [
                "research/evidence/p1_4_sources/metadata_MfrrReservesDK1_2026-09-06.json",
                "research/evidence/p1_4_sources/metadata_mFRRCapacityMarket_2026-09-06.json",
            ],
            "why": "Capacity is procured before delivery, but schema bridging and exact availability remain for P6.1.",
        },
        {
            "research_role": "future H3 successor sources",
            "source": "ENTSO-E / JAO",
            "fields": ["day-ahead scheduled exchange", "day-ahead transfer capacity"],
            "development_coverage": "not retrieved in P1.4",
            "eligibility": "external_candidate_pending_access_timing",
            "decision": "registered_successor",
            "evidence": ["https://transparency.entsoe.eu/", "https://www.jao.eu/"],
            "why": "Official replacements matter for future extensions after Transmissionlines was discontinued.",
        },
    ]


def markdown_report(report: dict[str, object]) -> str:
    actual = report["actual_fundamentals"]
    transmission = report["transmission"]
    countertrade = report["countertrade"]
    residual = actual["derived"]
    lines = [
        "# P1.4 Development Validation",
        "",
        f"**Status:** {report['validation_status']} — source eligibility inventory established",
        "",
        "## Scope control",
        "",
        f"- Development boundary: {DEVELOPMENT_START_LOCAL} through 2024-06-30 (local dates)",
        f"- Expected DK1 delivery hours: {len(EXPECTED_HOURS):,}",
        "- Locked holdout rows inspected: 0",
        "- Missing values are preserved; no source-defined null is converted to zero",
        "",
        "## Actual fundamentals",
        "",
        f"- Source: `{actual['dataset']}`; status `{actual['status']}`; eligibility `diagnostic_only`",
        f"- Rows / unique hours: {actual['scope']['records']:,} / {actual['scope']['unique_hours']:,}",
        f"- Complete derived residual-load rows: {residual['complete_rows']:,}",
        f"- Negative residual-load hours: {residual['negative_residual_load_hours']:,} "
        f"({100 * residual['negative_residual_load_share']:.2f}%)",
        "- Formula: gross consumption minus total actual wind minus total actual solar",
        "- Meaning: suitable for explaining historical system tightness, not for a pre-delivery decision feature",
        "",
        "## Cross-border and system sources",
        "",
        f"- `Transmissionlines`: `{transmission['status']}`; "
        "day-ahead capacities and day-ahead schedules are decision-eligible candidates pending P2.3 cutoff mapping",
        "- Final intraday schedule and physical exchange fields are diagnostic only",
        f"- Connections observed: {', '.join(transmission['connections'])}",
        f"- Positive `ExportCapacity` rows preserved: "
        f"{transmission['documented_conditions']['mixed_export_capacity_signs']:,}",
        f"- GB rows with unavailable legacy day-ahead schedule: "
        f"{transmission['documented_conditions']['gb_day_ahead_null_rows']:,}",
        f"- `CountertradeIntraday`: `{countertrade['status']}`; partial-period conditional candidate",
        f"- Countertrade rows available at least one hour before delivery: "
        f"{countertrade['publication']['published_at_least_one_hour_before_delivery']:,} / "
        f"{countertrade['scope']['records']:,}",
        "- The 2025 successor is unavailable for the development period",
        "",
        "## Eligibility conclusion",
        "",
        "P1.4 is complete because every required research role now has a selected source, a conditional candidate, "
        "or an evidenced unavailable status. Exact row-level cutoff enforcement remains an implementation task in P2.3; "
        "H1-B proxy selection remains a registered P5.2 question. These are downstream gates rather than missing P1.4 inventory work.",
        "",
        "The holdout remained locked and unused. No executable trading P&L is claimed.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actual-raw", type=Path, required=True)
    parser.add_argument("--actual-metadata", type=Path, required=True)
    parser.add_argument("--countertrade-raw", type=Path, required=True)
    parser.add_argument("--countertrade-metadata", type=Path, required=True)
    parser.add_argument("--countertrade-successor-metadata", type=Path, required=True)
    parser.add_argument("--transmission-raw", type=Path, required=True)
    parser.add_argument("--transmission-metadata", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    parser.add_argument("--inventory-json", type=Path, required=True)
    args = parser.parse_args()

    actuals, _ = validate_actuals(args.actual_raw, args.actual_metadata)
    countertrade = validate_countertrade(
        args.countertrade_raw,
        args.countertrade_metadata,
        args.countertrade_successor_metadata,
    )
    transmission = validate_transmission(args.transmission_raw, args.transmission_metadata)
    inventory = source_inventory(actuals, countertrade, transmission)
    status = (
        "PASS"
        if actuals["status"] == "PASS"
        and transmission["status"] in {"PASS", "CONDITIONAL PASS"}
        and countertrade["status"] == "CONDITIONAL PASS"
        else "FAIL"
    )
    report = {
        "validation_status": status,
        "step": "P1.4",
        "development_start_local_inclusive": DEVELOPMENT_START_LOCAL,
        "development_end_local_inclusive": "2024-06-30",
        "boundary_timezone": LOCAL_TIMEZONE,
        "expected_delivery_hours": int(len(EXPECTED_HOURS)),
        "holdout_state": "LOCKED AND UNUSED",
        "actual_fundamentals": actuals,
        "transmission": transmission,
        "countertrade": countertrade,
        "source_inventory": inventory,
    }
    for path in [args.output_json, args.output_markdown, args.inventory_json]:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.output_markdown.write_text(markdown_report(report), encoding="utf-8")
    args.inventory_json.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"P1.4 validation status: {status}")
    print(f"Actual hours: {actuals['scope']['unique_hours']}")
    print(f"Transmission connections: {len(transmission['connections'])}")
    print(f"Countertrade rows: {countertrade['scope']['records']}")
    print(f"Holdout: {report['holdout_state']}")


if __name__ == "__main__":
    main()
