"""Build the point-in-time-safe P2 development data foundation.

This module preserves the P1 raw responses, normalizes source timestamps,
creates a one-row-per-hour DK1 base table, and emits reviewable quality and
eligibility evidence.  It deliberately does not construct the spread target,
labels, or forecast revisions; those belong to P3 and P4.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


RUN_DATE = "2026-09-06"
EXPECTED_BALANCING_GAP = pd.Timestamp("2022-10-30T00:00:00Z")


@dataclass(frozen=True)
class SourceContract:
    dataset: str
    raw_path: Path
    p1_manifest_path: Path
    primary_key: tuple[str, ...]
    role: str


SOURCE_CONTRACTS = (
    SourceContract(
        "Forecasts_Hour",
        Path("data/raw/p1_1_validation/Forecasts_Hour_DK1_development_2022-01-01_2024-06-30.json"),
        Path("research/evidence/p1_1_forecasts_hour/development_extract_manifest_2026-09-06.json"),
        ("HourUTC", "PriceArea", "ForecastType"),
        "decision_eligible_fixed_horizon",
    ),
    SourceContract(
        "Elspotprices",
        Path("data/raw/p1_2_validation/Elspotprices_DK1_development_2022-01-01_2024-06-30.json"),
        Path("research/evidence/p1_2_elspotprices/development_extract_manifest_2026-09-06.json"),
        ("HourUTC", "PriceArea"),
        "decision_eligible_reference",
    ),
    SourceContract(
        "RegulatingBalancePowerdata",
        Path("data/raw/p1_3_validation/RegulatingBalancePowerdata_DK1_development_2022-01-01_2024-06-30.json"),
        Path("research/evidence/p1_3_regulating_balance_power/development_extract_manifest_2026-09-06.json"),
        ("HourUTC", "PriceArea"),
        "outcome",
    ),
    SourceContract(
        "ProductionConsumptionSettlement",
        Path("data/raw/p1_4_validation/ProductionConsumptionSettlement_DK1_development_2022-01-01_2024-06-30.json"),
        Path("research/evidence/p1_4_sources/development_extract_manifest_2026-09-06.json"),
        ("HourUTC", "PriceArea"),
        "diagnostic_only",
    ),
    SourceContract(
        "Transmissionlines",
        Path("data/raw/p1_4_validation/Transmissionlines_DK1_development_2022-01-01_2024-06-30.json"),
        Path("research/evidence/p1_4_sources/development_extract_manifest_2026-09-06.json"),
        ("HourUTC", "PriceArea", "ConnectedArea"),
        "mixed_by_field",
    ),
    SourceContract(
        "CountertradeIntraday",
        Path("data/raw/p1_4_validation/CountertradeIntraday_development_overlap_2023-04-18_2024-06-30.json"),
        Path("research/evidence/p1_4_sources/development_extract_manifest_2026-09-06.json"),
        ("HourUTC",),
        "conditional_decision_candidate",
    ),
)

METADATA_PATHS = {
    "Forecasts_Hour": Path(
        "research/evidence/p1_1_forecasts_hour/metadata_2026-09-05.json"
    ),
    "Elspotprices": Path(
        "research/evidence/p1_2_elspotprices/metadata_2026-09-06.json"
    ),
    "RegulatingBalancePowerdata": Path(
        "research/evidence/p1_3_regulating_balance_power/metadata_RegulatingBalancePowerdata_2026-09-06.json"
    ),
    "ProductionConsumptionSettlement": Path(
        "research/evidence/p1_4_sources/metadata_ProductionConsumptionSettlement_2026-09-06.json"
    ),
    "Transmissionlines": Path(
        "research/evidence/p1_4_sources/metadata_Transmissionlines_2026-09-06.json"
    ),
    "CountertradeIntraday": Path(
        "research/evidence/p1_4_sources/metadata_CountertradeIntraday_2026-09-06.json"
    ),
}


FORECAST_TYPE_SLUG = {
    "Offshore Wind": "offshore_wind",
    "Onshore Wind": "onshore_wind",
    "Solar": "solar",
}

ACTUAL_FIELDS = [
    "GrossConsumptionMWh",
    "OffshoreWindLt100MW_MWh",
    "OffshoreWindGe100MW_MWh",
    "OnshoreWindLt50kW_MWh",
    "OnshoreWindGe50kW_MWh",
    "SolarPowerLt10kW_MWh",
    "SolarPowerGe10Lt40kW_MWh",
    "SolarPowerGe40kW_MWh",
    "SolarPowerSelfConMWh",
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


def snake_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def load_config(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config/research_config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    holdout = config["periods"]["holdout"]
    if holdout["state"] != "locked" or holdout["fetch_allowed"] is not False:
        raise ValueError("P2 requires the holdout to remain locked and fetch-disabled.")
    return config


def expected_time_base(config: dict[str, Any]) -> pd.DataFrame:
    timezone_name = config["periods"]["boundary_timezone"]
    start = config["periods"]["development"]["start_date"]
    end_exclusive = config["periods"]["holdout"]["start_date"]
    local = pd.date_range(
        start,
        end_exclusive,
        inclusive="left",
        freq="h",
        tz=timezone_name,
    )
    utc = local.tz_convert("UTC")
    frame = pd.DataFrame(
        {
            "delivery_start_utc": utc,
            "delivery_start_local": local,
            "local_wall_time": [value.strftime("%Y-%m-%dT%H:%M:%S") for value in local],
            "local_date": [value.strftime("%Y-%m-%d") for value in local],
            "local_hour": [value.hour for value in local],
            "local_weekday": [value.day_name() for value in local],
            "utc_offset_minutes": [
                int(value.utcoffset().total_seconds() / 60) for value in local
            ],
            "is_dst": [bool(value.dst().total_seconds()) for value in local],
        }
    )
    frame["local_hour_occurrence"] = (
        frame.groupby("local_wall_time", sort=False).cumcount() + 1
    )
    frame["price_area"] = config["project"]["price_area"]
    # The decision snapshot contains information available strictly before this anchor.
    frame["decision_time_utc"] = frame["delivery_start_utc"]
    return frame


def p1_manifest_entry(repo_root: Path, contract: SourceContract) -> dict[str, Any]:
    manifest = json.loads((repo_root / contract.p1_manifest_path).read_text())
    if "files" in manifest:
        return next(item for item in manifest["files"] if item["dataset"] == contract.dataset)
    return manifest


def preserve_raw_provenance(
    repo_root: Path,
    evidence_dir: Path,
    contracts: tuple[SourceContract, ...] = SOURCE_CONTRACTS,
) -> dict[str, Any]:
    entries = []
    for contract in contracts:
        raw_path = repo_root / contract.raw_path
        metadata_path = repo_root / METADATA_PATHS[contract.dataset]
        if not raw_path.exists():
            raise FileNotFoundError(f"Required P1 raw response is missing: {raw_path}")
        if not metadata_path.exists():
            raise FileNotFoundError(
                f"Required P1 metadata snapshot is missing: {metadata_path}"
            )
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        records = payload.get("records", [])
        original = p1_manifest_entry(repo_root, contract)
        actual_hash = sha256(raw_path)
        expected_hash = original.get("sha256")
        if expected_hash and expected_hash != actual_hash:
            raise ValueError(f"Raw hash changed since P1: {contract.dataset}")
        entries.append(
            {
                "dataset": contract.dataset,
                "raw_file": str(contract.raw_path),
                "raw_response_preserved": True,
                "bytes": raw_path.stat().st_size,
                "sha256": actual_hash,
                "matches_p1_manifest": expected_hash == actual_hash,
                "p1_manifest": str(contract.p1_manifest_path),
                "metadata_snapshot": str(METADATA_PATHS[contract.dataset]),
                "metadata_sha256": sha256(metadata_path),
                "p1_retrieved_or_manifested_at_utc": original.get("retrieved_at_utc")
                or original.get("file_timestamp_utc")
                or manifest_created_at(repo_root, contract),
                "request_url": original.get("source_url") or original.get("request_url"),
                "request": original.get("request"),
                "api_reported_total": payload.get("total"),
                "records": len(records),
                "primary_key": list(contract.primary_key),
                "research_role": contract.role,
            }
        )

    result = {
        "step": "P2.2",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_organization": "Energinet",
        "raw_policy": "Exact API JSON responses are immutable and git-ignored; this committed manifest preserves request and hash evidence.",
        "pipeline_code": {
            "path": "src/p2_pipeline.py",
            "sha256": sha256(repo_root / "src/p2_pipeline.py"),
        },
        "research_config": {
            "path": "config/research_config.yaml",
            "sha256": sha256(repo_root / "config/research_config.yaml"),
        },
        "development_boundary": {
            "start_local_inclusive": "2022-01-01",
            "end_local_exclusive": "2024-07-01",
            "timezone": "Europe/Copenhagen",
        },
        "holdout": "LOCKED_AND_NOT_REQUESTED",
        "files": entries,
    }
    json_dump(evidence_dir / f"raw_provenance_{RUN_DATE}.json", result)
    return result


def manifest_created_at(repo_root: Path, contract: SourceContract) -> str | None:
    manifest = json.loads((repo_root / contract.p1_manifest_path).read_text())
    return manifest.get("created_at_utc")


def load_raw_frame(repo_root: Path, contract: SourceContract) -> pd.DataFrame:
    payload = json.loads((repo_root / contract.raw_path).read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError(f"{contract.dataset} has no records.")
    frame = pd.DataFrame(records)
    missing_key = [column for column in contract.primary_key if column not in frame]
    if missing_key:
        raise ValueError(f"{contract.dataset} is missing key fields {missing_key}")
    return frame


def attach_delivery_times(
    frame: pd.DataFrame,
    config: dict[str, Any],
    dataset: str,
) -> pd.DataFrame:
    result = frame.copy()
    timezone_name = config["periods"]["boundary_timezone"]
    start = pd.Timestamp(
        config["periods"]["development"]["start_date"], tz=timezone_name
    )
    end = pd.Timestamp(config["periods"]["holdout"]["start_date"], tz=timezone_name)
    result["delivery_start_utc"] = pd.to_datetime(
        result["HourUTC"], utc=True, errors="raise"
    )
    result["delivery_start_local"] = result["delivery_start_utc"].dt.tz_convert(
        timezone_name
    )
    in_scope = result["delivery_start_local"].ge(start) & result[
        "delivery_start_local"
    ].lt(end)
    if not in_scope.all():
        raise ValueError(f"{dataset} contains rows outside development.")
    if "HourDK" in result:
        expected_hour_dk = result["delivery_start_local"].dt.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        result["source_hour_dk_matches"] = result["HourDK"].eq(expected_hour_dk)
    result["decision_time_utc"] = result["delivery_start_utc"]
    return result


def normalize_sources(
    repo_root: Path,
    config: dict[str, Any],
    output_dir: Path,
) -> dict[str, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized: dict[str, pd.DataFrame] = {}
    for contract in SOURCE_CONTRACTS:
        frame = attach_delivery_times(
            load_raw_frame(repo_root, contract), config, contract.dataset
        )
        if frame.duplicated(list(contract.primary_key), keep=False).any():
            raise ValueError(f"Duplicate source primary keys in {contract.dataset}.")
        if "PriceArea" in frame and not frame["PriceArea"].eq("DK1").all():
            raise ValueError(f"Non-DK1 row in {contract.dataset}.")

        if contract.dataset == "Forecasts_Hour":
            unknown_types = set(frame["ForecastType"].dropna()) - set(
                FORECAST_TYPE_SLUG
            )
            if unknown_types:
                raise ValueError(f"Unknown forecast types: {sorted(unknown_types)}")
            frame["forecast_5h_available_at_cutoff"] = frame[
                "Forecast5Hour"
            ].notna()
            frame["forecast_1h_available_at_cutoff"] = frame[
                "Forecast1Hour"
            ].notna()
        elif contract.dataset == "Elspotprices":
            frame["spot_price_available_at_cutoff"] = frame["SpotPriceEUR"].notna()
        elif contract.dataset == "CountertradeIntraday":
            publication_naive = pd.to_datetime(
                frame["PublicationDate"], errors="coerce"
            )
            publication_local = publication_naive.dt.tz_localize(
                config["periods"]["boundary_timezone"],
                ambiguous="NaT",
                nonexistent="NaT",
            )
            frame["publication_time_utc"] = publication_local.dt.tz_convert("UTC")
            frame["published_before_decision_cutoff"] = frame[
                "publication_time_utc"
            ].lt(frame["decision_time_utc"])

        normalized[contract.dataset] = frame
        frame.to_parquet(
            output_dir / f"{snake_case(contract.dataset)}_development.parquet",
            index=False,
        )
    return normalized


def merge_one_to_one(
    master: pd.DataFrame,
    right: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    return master.merge(
        right,
        on="delivery_start_utc",
        how="left",
        validate="one_to_one",
        suffixes=(None, f"_{snake_case(dataset)}"),
    )


def forecast_wide(frame: pd.DataFrame) -> pd.DataFrame:
    selected = [
        "ForecastDayAhead",
        "ForecastIntraday",
        "Forecast5Hour",
        "Forecast1Hour",
    ]
    pieces = []
    for field in selected:
        pivot = frame.pivot(
            index="delivery_start_utc",
            columns="ForecastType",
            values=field,
        )
        pivot = pivot.rename(
            columns={
                forecast_type: f"forecast_{snake_case(field.removeprefix('Forecast'))}_{slug}_mwh_per_hour"
                for forecast_type, slug in FORECAST_TYPE_SLUG.items()
            }
        )
        pieces.append(pivot)
    result = pd.concat(pieces, axis=1).reset_index()
    for slug in FORECAST_TYPE_SLUG.values():
        result[f"forecast_pair_5h_1h_available_{slug}"] = (
            result[f"forecast_5_hour_{slug}_mwh_per_hour"].notna()
            & result[f"forecast_1_hour_{slug}_mwh_per_hour"].notna()
        )
    return result


def transmission_wide(frame: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for field in TRANSMISSION_FIELDS:
        pivot = frame.pivot(
            index="delivery_start_utc",
            columns="ConnectedArea",
            values=field,
        )
        pivot.columns = [
            f"transmission_{snake_case(field)}_{str(area).lower()}" for area in pivot.columns
        ]
        pieces.append(pivot)
    return pd.concat(pieces, axis=1).reset_index()


def build_hourly_base(
    normalized: dict[str, pd.DataFrame],
    config: dict[str, Any],
) -> pd.DataFrame:
    master = expected_time_base(config)

    spot = normalized["Elspotprices"][
        ["delivery_start_utc", "SpotPriceEUR", "SpotPriceDKK"]
    ].rename(
        columns={
            "SpotPriceEUR": "spot_price_eur_mwh",
            "SpotPriceDKK": "spot_price_dkk_mwh",
        }
    )
    master = merge_one_to_one(master, spot, "Elspotprices")

    balancing_fields = [
        "ImbalancePriceEUR",
        "BalancingPowerPriceUpEUR",
        "BalancingPowerPriceDownEUR",
        "ImbalanceMWh",
        "mFRRUpActBal",
        "mFRRDownActBal",
    ]
    balancing = normalized["RegulatingBalancePowerdata"][
        ["delivery_start_utc", *balancing_fields]
    ].rename(columns={field: snake_case(field) for field in balancing_fields})
    balancing = balancing.rename(
        columns={
            "imbalance_price_eur": "imbalance_price_eur_mwh",
            "balancing_power_price_up_eur": "balancing_power_price_up_eur_mwh",
            "balancing_power_price_down_eur": "balancing_power_price_down_eur_mwh",
        }
    )
    master = merge_one_to_one(master, balancing, "RegulatingBalancePowerdata")

    master = merge_one_to_one(
        master,
        forecast_wide(normalized["Forecasts_Hour"]),
        "Forecasts_Hour",
    )

    actual = normalized["ProductionConsumptionSettlement"][
        ["delivery_start_utc", *ACTUAL_FIELDS]
    ].rename(columns={field: f"actual_{snake_case(field)}" for field in ACTUAL_FIELDS})
    master = merge_one_to_one(master, actual, "ProductionConsumptionSettlement")

    master = merge_one_to_one(
        master,
        transmission_wide(normalized["Transmissionlines"]),
        "Transmissionlines",
    )

    countertrade = normalized["CountertradeIntraday"][
        [
            "delivery_start_utc",
            "Version",
            "VolumeUpMW",
            "VolumeDownMW",
            "publication_time_utc",
            "published_before_decision_cutoff",
        ]
    ].rename(
        columns={
            "Version": "countertrade_version",
            "VolumeUpMW": "countertrade_volume_up_mw",
            "VolumeDownMW": "countertrade_volume_down_mw",
            "publication_time_utc": "countertrade_publication_time_utc",
            "published_before_decision_cutoff": "countertrade_published_before_cutoff",
        }
    )
    master = merge_one_to_one(master, countertrade, "CountertradeIntraday")

    master["spot_price_present"] = master["spot_price_eur_mwh"].notna()
    master["balancing_outcome_present"] = master[
        "imbalance_price_eur_mwh"
    ].notna()
    master["actual_fundamentals_present"] = master[
        "actual_gross_consumption_mwh"
    ].notna()
    if any("spread" in column for column in master.columns):
        raise ValueError("P2 must not construct the P3 spread target.")
    return master


def availability_contract(
    normalized: dict[str, pd.DataFrame],
    evidence_dir: Path,
) -> dict[str, Any]:
    countertrade = normalized["CountertradeIntraday"]
    result = {
        "step": "P2.3",
        "status": "PASS_WITH_CONSERVATIVE_EXCLUSIONS",
        "decision_cutoff": {
            "anchor": "delivery_start_utc",
            "offset_minutes": 0,
            "semantics": "Snapshot immediately before delivery starts; information must be available strictly before the anchor.",
            "execution_claim": False,
            "reason": "The source says fixed 1h/5h forecasts are released before delivery and may be updated until one minute before delivery; the stored data do not retain exact update versions. The delivery-start anchor is the earliest cutoff supported without fabricating a historical minute-level vintage.",
        },
        "timestamp_mapping": {
            "canonical_join_key": "delivery_start_utc",
            "interpretation_timezone": "Europe/Copenhagen",
            "source_hour_dk_use": "validation_only",
            "dst_rule": "Retain both UTC-distinct repeated local hours and record local_hour_occurrence.",
            "request_boundaries": "Local dates, start inclusive and end exclusive.",
        },
        "field_availability": [
            {
                "source": "Forecasts_Hour",
                "fields": ["Forecast5Hour", "Forecast1Hour"],
                "class_at_cutoff": "decision_eligible",
                "rule": "Use only non-null same-hour fixed-horizon values; no minute-level or tick-vintage claim.",
            },
            {
                "source": "Forecasts_Hour",
                "fields": ["ForecastCurrent", "TimestampUTC", "TimestampDK"],
                "class_at_cutoff": "diagnostic_only",
                "rule": "Timestamp fields describe ForecastCurrent, not the fixed 5h/1h snapshots.",
            },
            {
                "source": "Elspotprices",
                "fields": ["SpotPriceEUR", "SpotPriceDKK"],
                "class_at_cutoff": "decision_eligible_reference",
                "rule": "Day-ahead market outcome is fixed before the delivery-hour cutoff.",
            },
            {
                "source": "RegulatingBalancePowerdata",
                "fields": ["ImbalancePriceEUR", "ImbalanceMWh", "mFRRUpActBal", "mFRRDownActBal"],
                "class_at_cutoff": "outcome",
                "rule": "Never enter the decision-time feature set.",
            },
            {
                "source": "ProductionConsumptionSettlement",
                "fields": ["all settlement fields"],
                "class_at_cutoff": "diagnostic_only",
                "rule": "Released and revised after delivery; retain only for mechanism analysis.",
            },
            {
                "source": "Transmissionlines",
                "fields": ["ImportCapacity", "ExportCapacity", "ScheduledExchangeDayAhead"],
                "class_at_cutoff": "decision_eligible_candidate",
                "rule": "Timing passes at the delivery-start cutoff; border-specific signs and legacy nulls remain gated to P6.1.",
            },
            {
                "source": "Transmissionlines",
                "fields": ["ScheduledExchangeIntraday", "PhysicalExchangeNonvalidated", "PhysicalExchangeSettlement"],
                "class_at_cutoff": "diagnostic_only",
                "rule": "Final or realized values lack historical pre-cutoff vintages.",
            },
            {
                "source": "CountertradeIntraday",
                "fields": ["VolumeUpMW", "VolumeDownMW"],
                "class_at_cutoff": "conditional_decision_candidate",
                "rule": "Use only rows with PublicationDate strictly before cutoff; absence is unknown, not zero, and overwritten prior versions cannot be reconstructed.",
                "stored_rows": int(len(countertrade)),
                "rows_published_before_cutoff": int(
                    countertrade["published_before_decision_cutoff"].fillna(False).sum()
                ),
                "rows_not_available_by_cutoff": int(
                    (~countertrade["published_before_decision_cutoff"].fillna(False)).sum()
                ),
            },
            {
                "source": "RegulatingBalancePowerdata",
                "fields": ["previous-hour label/spread"],
                "class_at_cutoff": "ex_post_reference_baseline_only",
                "rule": "The legacy source has no documented historical publication delay; y[t-1] is not promoted to a decision-eligible input.",
            },
        ],
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"availability_contract_{RUN_DATE}.json", result)
    return result


def source_quality(
    normalized: dict[str, pd.DataFrame],
    expected_hours: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    contract_by_name = {item.dataset: item for item in SOURCE_CONTRACTS}
    for dataset, frame in normalized.items():
        contract = contract_by_name[dataset]
        result[dataset] = {
            "records": int(len(frame)),
            "unique_hours": int(frame["delivery_start_utc"].nunique()),
            "expected_hours": expected_hours,
            "duplicate_key_rows": int(
                frame.duplicated(list(contract.primary_key), keep=False).sum()
            ),
            "hour_dk_mismatch_rows": int(
                (~frame.get("source_hour_dk_matches", pd.Series(True, index=frame.index))).sum()
            ),
            "first_delivery_utc": frame["delivery_start_utc"].min().isoformat(),
            "last_delivery_utc": frame["delivery_start_utc"].max().isoformat(),
        }
    return result


def validate_and_report(
    repo_root: Path,
    config: dict[str, Any],
    normalized: dict[str, pd.DataFrame],
    master: pd.DataFrame,
    processed_path: Path,
    evidence_dir: Path,
    raw_provenance: dict[str, Any],
    availability: dict[str, Any],
) -> dict[str, Any]:
    expected = expected_time_base(config)
    holdout_start_utc = pd.Timestamp(
        config["periods"]["holdout"]["start_date"],
        tz=config["periods"]["boundary_timezone"],
    ).tz_convert("UTC")
    balancing_missing = master.loc[
        master["imbalance_price_eur_mwh"].isna(), "delivery_start_utc"
    ].tolist()
    forecast_pair_counts = {
        slug: int(master[f"forecast_pair_5h_1h_available_{slug}"].fillna(False).sum())
        for slug in FORECAST_TYPE_SLUG.values()
    }
    source = source_quality(normalized, len(expected))
    critical_checks = {
        "hourly_base_rows_equal_expected": len(master) == len(expected) == 21887,
        "hourly_base_unique_utc": master["delivery_start_utc"].is_unique,
        "no_holdout_rows": bool(master["delivery_start_utc"].lt(holdout_start_utc).all()),
        "spot_complete": int(master["spot_price_eur_mwh"].isna().sum()) == 0,
        "balancing_has_only_documented_gap": balancing_missing
        == [EXPECTED_BALANCING_GAP],
        "actual_fundamentals_complete": int(
            master["actual_gross_consumption_mwh"].isna().sum()
        )
        == 0,
        "all_raw_hashes_match_p1": all(
            item["matches_p1_manifest"] for item in raw_provenance["files"]
        ),
        "all_source_primary_keys_unique": all(
            item["duplicate_key_rows"] == 0 for item in source.values()
        ),
        "all_source_hour_dk_values_match": all(
            item["hour_dk_mismatch_rows"] == 0 for item in source.values()
        ),
        "repeated_dst_hours_preserved": int(master["local_hour_occurrence"].max())
        == 2,
        "spread_not_built_in_p2": not any(
            "spread" in column for column in master.columns
        ),
    }
    report = {
        "step": "P2.5",
        "status": "PASS" if all(critical_checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "critical_checks": critical_checks,
        "scope": {
            "expected_hours": int(len(expected)),
            "hourly_base_rows": int(len(master)),
            "first_delivery_utc": master["delivery_start_utc"].min().isoformat(),
            "last_delivery_utc": master["delivery_start_utc"].max().isoformat(),
            "holdout_rows": int(master["delivery_start_utc"].ge(holdout_start_utc).sum()),
            "duplicated_utc_rows": int(
                master.duplicated(["delivery_start_utc"], keep=False).sum()
            ),
            "repeated_local_wall_times": int(master["local_wall_time"].duplicated(keep=False).sum()),
        },
        "source_quality": source,
        "selected_coverage": {
            "spot_price_missing_hours": int(master["spot_price_eur_mwh"].isna().sum()),
            "imbalance_price_missing_hours": int(
                master["imbalance_price_eur_mwh"].isna().sum()
            ),
            "imbalance_missing_utc": [value.isoformat() for value in balancing_missing],
            "actual_gross_consumption_missing_hours": int(
                master["actual_gross_consumption_mwh"].isna().sum()
            ),
            "forecast_5h_1h_pair_hours": forecast_pair_counts,
            "countertrade_rows_joined": int(
                master["countertrade_version"].notna().sum()
            ),
            "countertrade_rows_published_before_cutoff": int(
                master["countertrade_published_before_cutoff"].fillna(False).sum()
            ),
        },
        "missing_policy": {
            "source_missing": "Preserve as null and attach eligibility/coverage evidence; never replace with zero.",
            "observed_zero": "Retain as a real observation.",
            "documented_balancing_gap": EXPECTED_BALANCING_GAP.isoformat(),
            "countertrade_absence": "Unknown/no stored publication, never assumed to mean zero volume.",
        },
        "unit_contract": {
            "spot_price_eur_mwh": "EUR/MWh",
            "imbalance_price_eur_mwh": "EUR/MWh",
            "forecast_fields": "MWh per hour",
            "actual_fundamentals": "MWh",
            "countertrade_volumes": "MW",
            "transmission_fields": "source-defined MWh or MWh per hour; no cross-unit arithmetic in P2",
        },
        "eligibility_summary": {
            "decision_eligible": [
                "spot_price_eur_mwh",
                "non-null forecast_5_hour_*",
                "non-null forecast_1_hour_*",
            ],
            "conditional_candidates": [
                "transmission import/export capacity and day-ahead schedule",
                "countertrade rows published before cutoff",
            ],
            "outcome": ["imbalance and balancing fields"],
            "diagnostic_only": [
                "actual settlement fundamentals and exchange",
                "final intraday schedule and physical transmission flows",
            ],
        },
        "processed_file": str(processed_path.relative_to(repo_root)),
        "processed_sha256": sha256(processed_path),
        "processed_columns": list(master.columns),
        "processed_column_count": int(len(master.columns)),
        "availability_contract": f"research/evidence/p2_data_pipeline/availability_contract_{RUN_DATE}.json",
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"quality_report_{RUN_DATE}.json", report)
    render_quality_markdown(report, evidence_dir / f"quality_report_{RUN_DATE}.md")
    if report["status"] != "PASS":
        failed = [name for name, value in critical_checks.items() if not value]
        raise ValueError(f"P2 quality gate failed: {failed}")
    return report


def render_quality_markdown(report: dict[str, Any], path: Path) -> None:
    scope = report["scope"]
    coverage = report["selected_coverage"]
    lines = [
        "# P2 Development Data Quality Report",
        "",
        f"**Status:** {report['status']}",
        "**Holdout:** LOCKED AND UNUSED",
        "",
        "## Structural result",
        "",
        f"- Expected DK1 delivery hours: `{scope['expected_hours']:,}`",
        f"- Hourly base rows: `{scope['hourly_base_rows']:,}`",
        f"- Duplicate UTC rows: `{scope['duplicated_utc_rows']}`",
        f"- Holdout rows: `{scope['holdout_rows']}`",
        f"- First UTC delivery hour: `{scope['first_delivery_utc']}`",
        f"- Last UTC delivery hour: `{scope['last_delivery_utc']}`",
        "",
        "## Core coverage",
        "",
        f"- Spot price missing hours: `{coverage['spot_price_missing_hours']}`",
        f"- Imbalance price missing hours: `{coverage['imbalance_price_missing_hours']}`",
        f"- Preserved balancing gap: `{', '.join(coverage['imbalance_missing_utc'])}`",
        f"- Actual gross-consumption missing hours: `{coverage['actual_gross_consumption_missing_hours']}`",
        f"- Countertrade stored rows joined: `{coverage['countertrade_rows_joined']:,}`",
        f"- Countertrade rows published before cutoff: `{coverage['countertrade_rows_published_before_cutoff']:,}`",
        "",
        "| Forecast type | Valid same-hour 5h/1h pairs |",
        "|---|---:|",
    ]
    for forecast_type, count in coverage["forecast_5h_1h_pair_hours"].items():
        lines.append(f"| {forecast_type.replace('_', ' ').title()} | {count:,} |")
    lines.extend(
        [
            "",
            "## Quality decisions",
            "",
            "- UTC is the unique join key; Danish local time is retained for interpretation.",
            "- Both occurrences of a repeated DST local hour remain separate rows.",
            "- Missing source rows and null values remain missing; observed zeros remain zero.",
            "- Outcome and diagnostic columns are present for later research but are excluded from decision-time eligibility.",
            "- P2 does not compute spread, labels or forecast revisions.",
            "- No holdout row was requested, processed or inspected.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_join_evidence(
    repo_root: Path,
    normalized: dict[str, pd.DataFrame],
    master: pd.DataFrame,
    processed_path: Path,
    evidence_dir: Path,
) -> None:
    manifest = {
        "step": "P2.4",
        "status": "PASS",
        "join_type": "Expected development-hour spine with validated one-to-one or pivoted left joins",
        "canonical_key": ["delivery_start_utc", "price_area"],
        "hourly_base_rows": int(len(master)),
        "hourly_base_unique_hours": int(master["delivery_start_utc"].nunique()),
        "sources": {
            dataset: {
                "normalized_rows": int(len(frame)),
                "unique_hours": int(frame["delivery_start_utc"].nunique()),
            }
            for dataset, frame in normalized.items()
        },
        "processed_file": str(processed_path.relative_to(repo_root)),
        "processed_sha256": sha256(processed_path),
        "spread_created": False,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"join_manifest_{RUN_DATE}.json", manifest)

    missing = master["delivery_start_utc"].eq(EXPECTED_BALANCING_GAP)
    dst = master["local_hour_occurrence"].eq(2)
    sample = pd.concat(
        [master.head(2), master.loc[missing], master.loc[dst], master.tail(2)],
        ignore_index=True,
    ).drop_duplicates("delivery_start_utc")
    sample_columns = [
        "delivery_start_utc",
        "delivery_start_local",
        "local_wall_time",
        "local_hour_occurrence",
        "price_area",
        "decision_time_utc",
        "spot_price_eur_mwh",
        "imbalance_price_eur_mwh",
        "forecast_5_hour_offshore_wind_mwh_per_hour",
        "forecast_1_hour_offshore_wind_mwh_per_hour",
        "forecast_pair_5h_1h_available_offshore_wind",
    ]
    sample[sample_columns].to_csv(
        evidence_dir / f"hourly_base_audit_sample_{RUN_DATE}.csv", index=False
    )


def write_readme(evidence_dir: Path, quality: dict[str, Any]) -> None:
    coverage = quality["selected_coverage"]
    text = f"""# P2 Data Pipeline Evidence

**Status:** PASS — P2.1 through P2.5 completed on {RUN_DATE}

## What this phase proves

The six P1-preserved Energinet development responses can be acquired through a
date-bounded client, traced by immutable hashes, normalized to one UTC delivery
key, joined to a `{quality['scope']['hourly_base_rows']:,}`-hour DK1 base table,
and checked without requesting or processing the locked holdout.

## Step evidence

- **P2.1:** `p2_1_sample_manifest_{RUN_DATE}.json`, the saved bounded sample,
  client guard-rail tests and explicit 429/invalid-response handling
- **P2.2:** `raw_provenance_{RUN_DATE}.json`; every raw hash still matches its
  P1 manifest
- **P2.3:** `availability_contract_{RUN_DATE}.json`; UTC/local/DST mappings and
  the last-pre-delivery information cutoff are explicit
- **P2.4:** `join_manifest_{RUN_DATE}.json` and
  `hourly_base_audit_sample_{RUN_DATE}.csv`; the processed parquet remains
  local and git-ignored
- **P2.5:** `quality_report_{RUN_DATE}.md` and JSON

## Final structural facts

- Hourly base: `{quality['scope']['hourly_base_rows']:,}` unique DK1 delivery hours
- Spot-price gaps: `{coverage['spot_price_missing_hours']}`
- Balancing-price gaps: `{coverage['imbalance_price_missing_hours']}`; the known
  `2022-10-30T00:00:00Z` gap remains null
- Same-hour 5h/1h pairs: offshore
  `{coverage['forecast_5h_1h_pair_hours']['offshore_wind']:,}`, onshore
  `{coverage['forecast_5h_1h_pair_hours']['onshore_wind']:,}`, solar
  `{coverage['forecast_5h_1h_pair_hours']['solar']:,}`
- Holdout rows: `0`

P2 deliberately does not calculate the balancing spread, neutral band, labels
or 5h-to-1h revisions. Those transformations begin in P3 and P4 so the data
foundation remains auditable.
"""
    (evidence_dir / "README.md").write_text(text, encoding="utf-8")


def run(repo_root: Path) -> dict[str, Any]:
    config = load_config(repo_root)
    evidence_dir = repo_root / "research/evidence/p2_data_pipeline"
    normalized_dir = repo_root / "data/processed/p2/normalized"
    processed_path = repo_root / "data/processed/p2/hourly_base_development.parquet"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    processed_path.parent.mkdir(parents=True, exist_ok=True)

    raw_provenance = preserve_raw_provenance(repo_root, evidence_dir)
    normalized = normalize_sources(repo_root, config, normalized_dir)
    availability = availability_contract(normalized, evidence_dir)
    master = build_hourly_base(normalized, config)
    master.to_parquet(processed_path, index=False)
    write_join_evidence(repo_root, normalized, master, processed_path, evidence_dir)
    quality = validate_and_report(
        repo_root,
        config,
        normalized,
        master,
        processed_path,
        evidence_dir,
        raw_provenance,
        availability,
    )
    write_readme(evidence_dir, quality)
    return quality


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = run(args.repo_root.resolve())
    print(
        json.dumps(
            {
                "status": report["status"],
                "rows": report["scope"]["hourly_base_rows"],
                "columns": report["processed_column_count"],
                "holdout": report["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
