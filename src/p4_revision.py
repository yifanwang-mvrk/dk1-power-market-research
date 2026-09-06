"""Build and diagnose the P4 5h-to-1h renewable forecast revision variables.

P4.2 constructs the per-type and wind-aggregate revisions on the P2 hourly base,
reports the coverage and ``5h == 1h`` diagnostics required by the frozen P4.1
specification, and freezes the signed quantile and decile bucket edges.  It does
not join any outcome and runs no revision-outcome comparison; that is P4.3.  The
locked holdout is never read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


RUN_DATE = "2026-09-06"
EXPECTED_ROWS = 21_887
NEAR_ZERO_BANDS_MWH = (0.0, 1.0, 5.0, 10.0)
QUANTILE_EDGES = (0.20, 0.40, 0.60, 0.80)
DECILE_EDGES = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90)
RULE_THRESHOLD_QUANTILE = 0.60
NORMALIZATION_FLOOR_QUANTILE = 0.10

FORECAST_5H = {
    "offshore_wind": "forecast_5_hour_offshore_wind_mwh_per_hour",
    "onshore_wind": "forecast_5_hour_onshore_wind_mwh_per_hour",
    "solar": "forecast_5_hour_solar_mwh_per_hour",
}
FORECAST_1H = {
    "offshore_wind": "forecast_1_hour_offshore_wind_mwh_per_hour",
    "onshore_wind": "forecast_1_hour_onshore_wind_mwh_per_hour",
    "solar": "forecast_1_hour_solar_mwh_per_hour",
}

# Columns that must never appear in the P4.2 output: it is a decision-eligible
# revision table only. Outcomes join in P4.3.
FORBIDDEN_OUTPUT_COLUMNS = (
    "imbalance_price_eur_mwh",
    "balancing_power_price_up_eur_mwh",
    "balancing_power_price_down_eur_mwh",
    "balancing_spread_eur_mwh",
    "absolute_spread_eur_mwh",
    "spread_is_nonzero",
    "neutral_band_delta_eur_mwh",
    "target_label",
    "target_is_valid",
)

KEY_COLUMNS = (
    "delivery_start_utc",
    "delivery_start_local",
    "local_date",
    "local_hour",
    "local_weekday",
    "local_hour_occurrence",
    "utc_offset_minutes",
    "is_dst",
    "price_area",
    "decision_time_utc",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or None


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def load_p2_base(repo_root: Path) -> tuple[dict[str, Any], pd.DataFrame, Path]:
    config = yaml.safe_load(
        (repo_root / "config/research_config.yaml").read_text(encoding="utf-8")
    )
    holdout = config["periods"]["holdout"]
    if holdout["state"] not in ("locked", "evaluated") or holdout["fetch_allowed"] is not False:
        raise ValueError("P4 requires the holdout to remain locked and fetch-disabled.")

    input_path = repo_root / "data/processed/p2/hourly_base_development.parquet"
    p2_quality = json.loads(
        (
            repo_root
            / "research/evidence/p2_data_pipeline"
            / f"quality_report_{RUN_DATE}.json"
        ).read_text(encoding="utf-8")
    )
    if p2_quality["status"] != "PASS":
        raise ValueError("The frozen P2 quality gate is not PASS.")
    if sha256(input_path) != p2_quality["processed_sha256"]:
        raise ValueError("The P2 hourly base hash no longer matches its P2 evidence.")

    frame = pd.read_parquet(input_path)
    required = set(KEY_COLUMNS) | set(FORECAST_5H.values()) | set(FORECAST_1H.values())
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"P2 hourly base is missing required columns: {sorted(missing)}")
    if len(frame) != EXPECTED_ROWS or not frame["delivery_start_utc"].is_unique:
        raise ValueError("P2 hourly base does not have the frozen unique-hour shape.")
    if not frame["price_area"].eq(config["project"]["price_area"]).all():
        raise ValueError("P2 hourly base contains a non-DK1 row.")
    holdout_start = pd.Timestamp(
        holdout["start_date"], tz=config["periods"]["boundary_timezone"]
    ).tz_convert("UTC")
    if frame["delivery_start_utc"].ge(holdout_start).any():
        raise ValueError("P2 hourly base contains a locked-holdout row.")
    return config, frame, input_path


def build_revisions(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for kind in ("offshore_wind", "onshore_wind", "solar"):
        f5 = result[FORECAST_5H[kind]]
        f1 = result[FORECAST_1H[kind]]
        both = f5.notna() & f1.notna()
        result[f"revision_{kind}_mwh"] = (f1 - f5).where(both)
        result[f"revision_{kind}_available"] = both
        result[f"revision_{kind}_5h_eq_1h"] = both & f5.eq(f1)

    off5, off1 = result[FORECAST_5H["offshore_wind"]], result[FORECAST_1H["offshore_wind"]]
    on5, on1 = result[FORECAST_5H["onshore_wind"]], result[FORECAST_1H["onshore_wind"]]
    wind_ok = off5.notna() & off1.notna() & on5.notna() & on1.notna()
    result["wind_revision_available"] = wind_ok
    result["wind_revision_mwh"] = ((off1 - off5) + (on1 - on5)).where(wind_ok)
    result["wind_forecast_5h_mwh"] = (off5 + on5).where(off5.notna() & on5.notna())
    result["wind_revision_5h_eq_1h"] = wind_ok & off5.eq(off1) & on5.eq(on1)

    s5, s1 = result[FORECAST_5H["solar"]], result[FORECAST_1H["solar"]]
    result["solar_revision_available"] = result["revision_solar_available"]
    result["solar_revision_mwh"] = result["revision_solar_mwh"]
    result["solar_both_horizons_positive"] = (
        result["solar_revision_available"] & s5.gt(0) & s1.gt(0)
    )
    return result


def normalization_floor(wind_forecast_5h: pd.Series) -> float:
    positive = wind_forecast_5h.dropna()
    positive = positive.loc[positive > 0]
    return float(positive.quantile(NORMALIZATION_FLOOR_QUANTILE, interpolation="linear"))


def add_normalized_revision(frame: pd.DataFrame, floor: float) -> pd.DataFrame:
    result = frame.copy()
    denom_ok = result["wind_forecast_5h_mwh"].ge(floor)
    eligible = result["wind_revision_available"] & denom_ok
    result["wind_revision_normalized"] = (
        result["wind_revision_mwh"] / result["wind_forecast_5h_mwh"]
    ).where(eligible)
    result["wind_revision_normalized_eligible"] = eligible
    return result


def _bucketize(
    values: pd.Series, quantiles: tuple[float, ...]
) -> tuple[pd.Series, list[float], str]:
    clean = values.dropna()
    raw_edges = [
        float(clean.quantile(q, interpolation="linear")) for q in quantiles
    ]
    unique_edges = sorted(dict.fromkeys(round(edge, 9) for edge in raw_edges))
    if len(unique_edges) == len(raw_edges):
        note = "edges strictly increasing"
    else:
        note = (
            f"duplicate quantile edges collapsed from {len(raw_edges)} to "
            f"{len(unique_edges)} interior cut points (mass point near zero)"
        )
    bins = [-math.inf, *unique_edges, math.inf]
    labels = list(range(1, len(bins)))
    bucket = pd.cut(values, bins=bins, labels=labels, include_lowest=True, right=True)
    return bucket.astype("Int64"), unique_edges, note


def freeze_buckets(
    values: pd.Series, name: str, with_rule_threshold: bool
) -> tuple[dict[str, Any], pd.Series, pd.Series]:
    quintile_bucket, quintile_edges, quintile_note = _bucketize(values, QUANTILE_EDGES)
    decile_bucket, decile_edges, decile_note = _bucketize(values, DECILE_EDGES)
    report: dict[str, Any] = {
        "variable": name,
        "available_observations": int(values.notna().sum()),
        "quantile_scheme": {
            "requested_quantiles": list(QUANTILE_EDGES),
            "interior_edges": quintile_edges,
            "tie_handling": quintile_note,
            "group_sizes": {
                int(k): int(v)
                for k, v in quintile_bucket.value_counts().sort_index().items()
            },
        },
        "decile_scheme": {
            "requested_quantiles": list(DECILE_EDGES),
            "interior_edges": decile_edges,
            "tie_handling": decile_note,
            "group_sizes": {
                int(k): int(v)
                for k, v in decile_bucket.value_counts().sort_index().items()
            },
        },
    }
    if with_rule_threshold:
        report["rule_threshold_c"] = {
            "definition": "Q60 of abs(wind_revision_mwh), development only",
            "quantile": RULE_THRESHOLD_QUANTILE,
            "value_mwh": float(
                values.abs().quantile(RULE_THRESHOLD_QUANTILE, interpolation="linear")
            ),
        }
    return report, quintile_bucket, decile_bucket


def near_zero_bands(revision: pd.Series) -> dict[str, Any]:
    available = revision.dropna()
    total = int(len(available))
    bands = {}
    for edge in NEAR_ZERO_BANDS_MWH:
        if edge == 0.0:
            count = int(available.eq(0).sum())
            key = "exactly_zero"
        else:
            count = int(available.abs().le(edge).sum())
            key = f"abs_le_{edge:g}_mwh"
        bands[key] = {"count": count, "share": (count / total) if total else None}
    return bands


def diagnostics(frame: pd.DataFrame) -> dict[str, Any]:
    total = int(len(frame))
    per_type: dict[str, Any] = {}
    for kind in ("offshore_wind", "onshore_wind", "solar"):
        available = int(frame[f"revision_{kind}_available"].sum())
        eq = int(frame[f"revision_{kind}_5h_eq_1h"].sum())
        per_type[kind] = {
            "available_pairs": available,
            "dropped_missing_horizon": total - available,
            "five_h_equals_one_h_exact": eq,
            "five_h_equals_one_h_share_of_available": (eq / available) if available else None,
            "near_zero_bands": near_zero_bands(frame[f"revision_{kind}_mwh"]),
        }

    wind_available = int(frame["wind_revision_available"].sum())
    wind_eq = int(frame["wind_revision_5h_eq_1h"].sum())
    solar_available = int(frame["solar_revision_available"].sum())
    solar_both_positive = int(frame["solar_both_horizons_positive"].sum())
    return {
        "total_development_hours": total,
        "per_forecast_type": per_type,
        "wind_aggregate": {
            "available_pairs": wind_available,
            "dropped_missing_any_wind_horizon": total - wind_available,
            "neither_wind_forecast_updated_exact": wind_eq,
            "neither_wind_forecast_updated_share": (wind_eq / wind_available)
            if wind_available
            else None,
            "near_zero_bands": near_zero_bands(frame["wind_revision_mwh"]),
        },
        "solar_sample_split": {
            "all_numeric_pairs": solar_available,
            "both_horizons_positive": solar_both_positive,
            "zero_or_missing_daylight": solar_available - solar_both_positive,
        },
    }


def audit_sample(frame: pd.DataFrame, output_path: Path) -> None:
    parts = [frame.head(2), frame.tail(2)]
    for bucket in range(1, 6):
        parts.append(frame.loc[frame["wind_revision_quintile"].eq(bucket)].head(1))
    parts.append(frame.loc[frame["wind_revision_5h_eq_1h"]].head(1))
    parts.append(frame.loc[frame["wind_revision_mwh"].abs().le(1)].head(1))
    parts.append(frame.loc[~frame["wind_revision_available"]].head(1))
    parts.append(frame.loc[frame["revision_solar_5h_eq_1h"]].head(1))
    sample = (
        pd.concat(parts)
        .drop_duplicates("delivery_start_utc")
        .sort_values("delivery_start_utc")
    )
    columns = [
        "delivery_start_utc",
        "delivery_start_local",
        "local_hour_occurrence",
        "price_area",
        FORECAST_5H["offshore_wind"],
        FORECAST_1H["offshore_wind"],
        FORECAST_5H["onshore_wind"],
        FORECAST_1H["onshore_wind"],
        FORECAST_5H["solar"],
        FORECAST_1H["solar"],
        "revision_offshore_wind_mwh",
        "revision_onshore_wind_mwh",
        "revision_solar_mwh",
        "wind_revision_mwh",
        "wind_forecast_5h_mwh",
        "wind_revision_normalized",
        "wind_revision_quintile",
        "wind_revision_decile",
        "wind_revision_available",
        "solar_both_horizons_positive",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample[columns].to_csv(output_path, index=False)


def build_output_frame(frame: pd.DataFrame) -> pd.DataFrame:
    keep = [
        *KEY_COLUMNS,
        *FORECAST_5H.values(),
        *FORECAST_1H.values(),
        "revision_offshore_wind_mwh",
        "revision_offshore_wind_available",
        "revision_offshore_wind_5h_eq_1h",
        "revision_onshore_wind_mwh",
        "revision_onshore_wind_available",
        "revision_onshore_wind_5h_eq_1h",
        "revision_solar_mwh",
        "revision_solar_available",
        "revision_solar_5h_eq_1h",
        "wind_revision_mwh",
        "wind_revision_available",
        "wind_revision_5h_eq_1h",
        "wind_forecast_5h_mwh",
        "wind_revision_normalized",
        "wind_revision_normalized_eligible",
        "wind_revision_quintile",
        "wind_revision_decile",
        "solar_revision_mwh",
        "solar_revision_available",
        "solar_both_horizons_positive",
        "solar_revision_quintile",
        "solar_revision_decile",
        "solar_revision_bothpos_quintile",
        "solar_revision_bothpos_decile",
    ]
    output = frame[keep].copy()
    present_forbidden = [c for c in FORBIDDEN_OUTPUT_COLUMNS if c in output.columns]
    if present_forbidden:
        raise ValueError(f"P4.2 output must not carry outcomes: {present_forbidden}")
    return output


def validate_and_report(
    repo_root: Path,
    config: dict[str, Any],
    input_path: Path,
    source: pd.DataFrame,
    output: pd.DataFrame,
    bucket_freeze: dict[str, Any],
    output_path: Path,
    evidence_dir: Path,
) -> dict[str, Any]:
    holdout_start = pd.Timestamp(
        config["periods"]["holdout"]["start_date"],
        tz=config["periods"]["boundary_timezone"],
    ).tz_convert("UTC")

    revision_null_checks = {}
    for kind in ("offshore_wind", "onshore_wind", "solar"):
        f5 = source[FORECAST_5H[kind]]
        f1 = source[FORECAST_1H[kind]]
        expected_available = f5.notna() & f1.notna()
        revision_null_checks[kind] = bool(
            source[f"revision_{kind}_mwh"].notna().eq(expected_available).all()
        )

    off5, off1 = source[FORECAST_5H["offshore_wind"]], source[FORECAST_1H["offshore_wind"]]
    on5, on1 = source[FORECAST_5H["onshore_wind"]], source[FORECAST_1H["onshore_wind"]]
    wind_expected = off5.notna() & off1.notna() & on5.notna() & on1.notna()

    quintile_sizes = bucket_freeze["wind_revision"]["quantile_scheme"]["group_sizes"]
    quintile_edges = bucket_freeze["wind_revision"]["quantile_scheme"]["interior_edges"]

    normalized_floor = bucket_freeze["normalization_floor_mwh"]
    normalized_rows = output.loc[output["wind_revision_normalized"].notna()]

    critical_checks = {
        "input_hash_matches_frozen_p2": sha256(input_path)
        == json.loads(
            (
                repo_root
                / "research/evidence/p2_data_pipeline"
                / f"quality_report_{RUN_DATE}.json"
            ).read_text(encoding="utf-8")
        )["processed_sha256"],
        "rows_equal_p2": len(output) == EXPECTED_ROWS,
        "key_unique": output["delivery_start_utc"].is_unique,
        "dk1_only": bool(output["price_area"].eq(config["project"]["price_area"]).all()),
        "no_holdout_rows": bool(output["delivery_start_utc"].lt(holdout_start).all()),
        "revision_null_iff_horizon_null": all(revision_null_checks.values()),
        "wind_revision_null_iff_any_wind_horizon_null": bool(
            output["wind_revision_mwh"].notna().eq(wind_expected).all()
        ),
        "wind_quintile_edges_strictly_increasing": quintile_edges
        == sorted(quintile_edges)
        and len(set(quintile_edges)) == len(quintile_edges),
        "wind_quintile_covers_all_available": sum(quintile_sizes.values())
        == int(output["wind_revision_mwh"].notna().sum()),
        "output_has_no_outcome_columns": not [
            c for c in FORBIDDEN_OUTPUT_COLUMNS if c in output.columns
        ],
        "normalized_only_at_or_above_floor": bool(
            normalized_rows["wind_forecast_5h_mwh"].ge(normalized_floor).all()
        ),
        "no_outcome_comparison_performed": True,
    }
    quality = {
        "step": "P4.2",
        "status": "PASS" if all(critical_checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "input_file": str(input_path.relative_to(repo_root)),
        "input_sha256": sha256(input_path),
        "output_file": str(output_path.relative_to(repo_root)),
        "output_sha256": sha256(output_path),
        "rows": int(len(output)),
        "columns": int(len(output.columns)),
        "critical_checks": critical_checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        failed = [name for name, ok in critical_checks.items() if not ok]
        raise ValueError(f"P4.2 quality gate failed: {failed}")
    return quality


def write_markdown(evidence_dir: Path, diag: dict[str, Any], freeze: dict[str, Any]) -> None:
    wind = diag["wind_aggregate"]
    solar = diag["solar_sample_split"]
    qedges = freeze["wind_revision"]["quantile_scheme"]["interior_edges"]
    qsizes = freeze["wind_revision"]["quantile_scheme"]["group_sizes"]
    c = freeze["wind_revision"]["rule_threshold_c"]["value_mwh"]
    text = f"""# P4.2 Revision Build and Diagnostics

**Status:** PASS — built on the frozen P2 hourly base on {RUN_DATE}
**Scope:** decision-eligible revision variables only; no outcome joined
**Holdout:** LOCKED AND UNUSED

## Coverage

| Series | Available pairs | Dropped (missing horizon) |
|---|---:|---:|
| Offshore wind | {diag['per_forecast_type']['offshore_wind']['available_pairs']:,} | {diag['per_forecast_type']['offshore_wind']['dropped_missing_horizon']:,} |
| Onshore wind | {diag['per_forecast_type']['onshore_wind']['available_pairs']:,} | {diag['per_forecast_type']['onshore_wind']['dropped_missing_horizon']:,} |
| Solar | {diag['per_forecast_type']['solar']['available_pairs']:,} | {diag['per_forecast_type']['solar']['dropped_missing_horizon']:,} |
| **Wind aggregate (primary)** | **{wind['available_pairs']:,}** | **{wind['dropped_missing_any_wind_horizon']:,}** |

## Did the forecast actually change? (P4.1 R1 diagnostic)

- Wind aggregate hours where neither offshore nor onshore forecast moved
  (`5h == 1h` exact): {wind['neither_wind_forecast_updated_exact']:,}
  ({wind['neither_wind_forecast_updated_share']:.2%} of available)
- Wind `abs(revision) <= 1 MWh`: {wind['near_zero_bands']['abs_le_1_mwh']['count']:,}
  ({wind['near_zero_bands']['abs_le_1_mwh']['share']:.2%})
- Wind `abs(revision) <= 5 MWh`: {wind['near_zero_bands']['abs_le_5_mwh']['count']:,}
  ({wind['near_zero_bands']['abs_le_5_mwh']['share']:.2%})
- Solar hours where `5h == 1h` exact:
  {diag['per_forecast_type']['solar']['five_h_equals_one_h_exact']:,}
  ({diag['per_forecast_type']['solar']['five_h_equals_one_h_share_of_available']:.2%})

## Solar sample split (D021)

- All numeric pairs: {solar['all_numeric_pairs']:,}
- Both horizons positive (daytime subset): {solar['both_horizons_positive']:,}
- Zero or non-positive daylight rows: {solar['zero_or_missing_daylight']:,}

## Frozen wind_revision buckets (signed, development only)

Interior quintile edges (MWh): {", ".join(f"{e:+.3f}" for e in qedges)}
Tie handling: {freeze['wind_revision']['quantile_scheme']['tie_handling']}

| Quintile bucket | Size |
|---|---:|
| 1 (most negative revision) | {qsizes.get(1, 0):,} |
| 2 | {qsizes.get(2, 0):,} |
| 3 (middle) | {qsizes.get(3, 0):,} |
| 4 | {qsizes.get(4, 0):,} |
| 5 (most positive revision) | {qsizes.get(5, 0):,} |

Transparent-rule threshold `c` = Q60 of `abs(wind_revision)` =
`{c:.3f} MWh` (frozen; the rule predicts DOWN if revision > c, UP if < -c).

Normalization floor for `wind_forecast_5h` (Q10 of positive values):
`{freeze['normalization_floor_mwh']:.3f} MWh`.

## What P4.2 does not do

No outcome column is joined and no revision-outcome statistic is computed. The
contingency table, association and transparent-rule scoring are P4.3.
"""
    (evidence_dir / f"p4_2_diagnostics_{RUN_DATE}.md").write_text(text, encoding="utf-8")


def run(repo_root: Path) -> dict[str, Any]:
    config, base, input_path = load_p2_base(repo_root)
    evidence_dir = repo_root / "research/evidence/p4_h2_revision"
    output_path = repo_root / "data/processed/p4/revision_development.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    frame = build_revisions(base)
    floor = normalization_floor(frame["wind_forecast_5h_mwh"])
    frame = add_normalized_revision(frame, floor)

    wind_freeze, wind_quintile, wind_decile = freeze_buckets(
        frame["wind_revision_mwh"], "wind_revision_mwh", with_rule_threshold=True
    )
    frame["wind_revision_quintile"] = wind_quintile
    frame["wind_revision_decile"] = wind_decile

    solar_freeze, solar_quintile, solar_decile = freeze_buckets(
        frame["solar_revision_mwh"], "solar_revision_mwh", with_rule_threshold=False
    )
    frame["solar_revision_quintile"] = solar_quintile
    frame["solar_revision_decile"] = solar_decile

    bothpos = frame["solar_revision_mwh"].where(frame["solar_both_horizons_positive"])
    solar_bothpos_freeze, solar_bp_quintile, solar_bp_decile = freeze_buckets(
        bothpos, "solar_revision_mwh_both_positive", with_rule_threshold=False
    )
    frame["solar_revision_bothpos_quintile"] = solar_bp_quintile
    frame["solar_revision_bothpos_decile"] = solar_bp_decile

    bucket_freeze = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_period": config["periods"]["development"],
        "input_file": str(input_path.relative_to(repo_root)),
        "input_sha256": sha256(input_path),
        "normalization_floor_mwh": floor,
        "wind_revision": wind_freeze,
        "solar_revision_all_pairs": solar_freeze,
        "solar_revision_both_positive": solar_bothpos_freeze,
        "holdout": "LOCKED_AND_UNUSED",
    }

    diag = diagnostics(frame)
    diag_report = {
        "step": "P4.2",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "outcome_joined": False,
        "revision_formula": "Forecast1Hour - Forecast5Hour per HourUTC + PriceArea + ForecastType",
        "wind_aggregate_rule": "offshore + onshore, only when all four horizon fields are non-null",
        **diag,
        "holdout": "LOCKED_AND_UNUSED",
    }

    output = build_output_frame(frame)
    output.to_parquet(output_path, index=False)

    json_dump(evidence_dir / f"p4_2_revision_build_{RUN_DATE}.json", diag_report)
    json_dump(evidence_dir / f"p4_2_bucket_freeze_{RUN_DATE}.json", bucket_freeze)
    audit_sample(frame, evidence_dir / f"revision_audit_sample_{RUN_DATE}.csv")
    quality = validate_and_report(
        repo_root, config, input_path, frame, output, bucket_freeze, output_path, evidence_dir
    )
    write_markdown(evidence_dir, diag, bucket_freeze)
    return {"quality": quality, "diagnostics": diag_report, "buckets": bucket_freeze}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = run(args.repo_root.resolve())
    wind = report["diagnostics"]["wind_aggregate"]
    print(
        json.dumps(
            {
                "status": report["quality"]["status"],
                "rows": report["quality"]["rows"],
                "columns": report["quality"]["columns"],
                "wind_revision_available": wind["available_pairs"],
                "wind_5h_eq_1h_exact": wind["neither_wind_forecast_updated_exact"],
                "wind_quintile_edges_mwh": report["buckets"]["wind_revision"][
                    "quantile_scheme"
                ]["interior_edges"],
                "rule_threshold_c_mwh": report["buckets"]["wind_revision"][
                    "rule_threshold_c"
                ]["value_mwh"],
                "holdout": report["quality"]["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
