"""Construct and validate the frozen P3 development target.

P3 converts the P2 hourly base into a same-hour balancing spread, freezes the
development-only neutral-band threshold, assigns the three outcome classes and
documents the mandatory baselines.  The locked holdout is never read.
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
LABEL_ORDER = ("UP", "DOWN", "NEUTRAL")
EXPECTED_ROWS = 21_887
EXPECTED_BALANCING_GAP = pd.Timestamp("2022-10-30T00:00:00Z")


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


def load_inputs(repo_root: Path) -> tuple[dict[str, Any], pd.DataFrame, Path]:
    config_path = repo_root / "config/research_config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    holdout = config["periods"]["holdout"]
    if holdout["state"] not in ("locked", "evaluated") or holdout["fetch_allowed"] is not False:
        raise ValueError("P3 requires the holdout to remain locked and fetch-disabled.")

    input_path = repo_root / config["neutral_band"]["input_file"]
    p2_quality_path = (
        repo_root
        / "research/evidence/p2_data_pipeline"
        / f"quality_report_{RUN_DATE}.json"
    )
    p2_quality = json.loads(p2_quality_path.read_text(encoding="utf-8"))
    if p2_quality["status"] != "PASS":
        raise ValueError("The frozen P2 quality gate is not PASS.")
    expected_hash = p2_quality["processed_sha256"]
    actual_hash = sha256(input_path)
    if actual_hash != expected_hash:
        raise ValueError("The P2 hourly base hash no longer matches its P2 evidence.")

    frame = pd.read_parquet(input_path)
    required = {
        "delivery_start_utc",
        "delivery_start_local",
        "local_wall_time",
        "local_hour_occurrence",
        "price_area",
        "spot_price_eur_mwh",
        "imbalance_price_eur_mwh",
    }
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


def build_spread(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["balancing_spread_eur_mwh"] = (
        result["imbalance_price_eur_mwh"] - result["spot_price_eur_mwh"]
    )
    result["absolute_spread_eur_mwh"] = result[
        "balancing_spread_eur_mwh"
    ].abs()
    result["spread_is_nonzero"] = result["balancing_spread_eur_mwh"].ne(0) & result[
        "balancing_spread_eur_mwh"
    ].notna()
    return result


def calculate_delta(spread: pd.Series) -> dict[str, Any]:
    valid = spread.dropna()
    nonzero_absolute = valid.loc[valid.ne(0)].abs().sort_values(ignore_index=True)
    if nonzero_absolute.empty:
        raise ValueError("No valid nonzero development spreads are available.")

    quantile = 0.25
    position = (len(nonzero_absolute) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    upper_weight = position - lower_index
    delta = float(
        nonzero_absolute.quantile(quantile, interpolation="linear")
    )
    return {
        "quantile": quantile,
        "population": "abs(spread) where spread is valid and nonzero, development only",
        "valid_spreads": int(len(valid)),
        "missing_spreads": int(spread.isna().sum()),
        "zero_spreads_excluded": int(valid.eq(0).sum()),
        "nonzero_absolute_spreads": int(len(nonzero_absolute)),
        "quantile_method": "linear",
        "calculation": "pandas.Series.quantile(q=0.25, interpolation='linear')",
        "zero_based_position": float(position),
        "lower_index": int(lower_index),
        "upper_index": int(upper_index),
        "lower_value": float(nonzero_absolute.iloc[lower_index]),
        "upper_value": float(nonzero_absolute.iloc[upper_index]),
        "upper_weight": float(upper_weight),
        "delta_eur_mwh": delta,
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
    }


def assign_labels(frame: pd.DataFrame, delta: float) -> pd.DataFrame:
    result = frame.copy()
    spread = result["balancing_spread_eur_mwh"]
    labels = pd.Series(pd.NA, index=result.index, dtype="string")
    labels.loc[spread.gt(delta)] = "UP"
    labels.loc[spread.lt(-delta)] = "DOWN"
    labels.loc[spread.notna() & spread.abs().le(delta)] = "NEUTRAL"
    result["neutral_band_delta_eur_mwh"] = delta
    result["target_label"] = labels
    result["target_is_valid"] = spread.notna()
    return result


def class_distribution(labels: pd.Series) -> dict[str, Any]:
    valid = labels.dropna()
    counts = {label: int(valid.eq(label).sum()) for label in LABEL_ORDER}
    shares = {label: counts[label] / len(valid) for label in LABEL_ORDER}
    return {
        "denominator_valid_labels": int(len(valid)),
        "missing_labels": int(labels.isna().sum()),
        "counts": counts,
        "shares": shares,
    }


def baseline_report(frame: pd.DataFrame) -> dict[str, Any]:
    labels = frame["target_label"]
    distribution = class_distribution(labels)
    counts = distribution["counts"]
    majority = max(LABEL_ORDER, key=lambda label: counts[label])
    valid_count = distribution["denominator_valid_labels"]

    previous_label = labels.shift(1)
    previous_time = frame["delivery_start_utc"].shift(1)
    consecutive = (frame["delivery_start_utc"] - previous_time).eq(
        pd.Timedelta(hours=1)
    )
    eligible = labels.notna() & previous_label.notna() & consecutive
    actual = labels.loc[eligible]
    predicted = previous_label.loc[eligible]
    confusion = pd.crosstab(actual, predicted).reindex(
        index=LABEL_ORDER, columns=LABEL_ORDER, fill_value=0
    )
    correct = int(actual.eq(predicted).sum())

    return {
        "step": "P3.4",
        "status": "PASS_WITH_PERSISTENCE_AS_EX_POST_REFERENCE",
        "development_base_rates": distribution,
        "majority_class": {
            "definition": "Fit on training labels only, then always predict the training majority class.",
            "development_wide_descriptive_majority": majority,
            "development_wide_descriptive_correct": counts[majority],
            "development_wide_descriptive_accuracy": counts[majority] / valid_count,
            "evaluation_rule": "For every future validation segment, refit using only its preceding training segment.",
            "decision_availability": "eligible_when_fit_on_training_only",
        },
        "persistence": {
            "formula": "predicted_label_t = observed_label_t_minus_1",
            "eligible_pairs": int(eligible.sum()),
            "excluded_pairs": int(len(frame) - eligible.sum()),
            "correct": correct,
            "development_wide_descriptive_accuracy": correct / int(eligible.sum()),
            "confusion_matrix_actual_rows_predicted_columns": {
                row: {column: int(confusion.loc[row, column]) for column in LABEL_ORDER}
                for row in LABEL_ORDER
            },
            "availability_status": "ex_post_reference_only",
            "decision_feature_eligible": False,
            "reason": "The legacy balancing dataset does not document historical outcome publication delay, so y[t-1] cannot be proven available at the last-pre-delivery cutoff.",
        },
        "availability_safe_supplemental": {
            "name": "hour_of_week_training_majority",
            "definition": "Within each training segment, select the most common label for each Danish local weekday-hour; fall back to the global training majority.",
            "inputs_at_prediction": ["local_weekday", "local_hour"],
            "fit_scope": "training_rows_only",
            "decision_availability": "eligible",
            "evaluation_status": "registered_before_evaluation; performance belongs to later time-split testing",
            "note": "This is an availability-safe reference, not a replacement presented as outcome persistence.",
        },
        "interpretation": "All P3 accuracy values are development-wide descriptive diagnostics, not out-of-sample model evidence.",
        "holdout": "LOCKED_AND_UNUSED",
    }


def audit_sample(frame: pd.DataFrame, output_path: Path, delta: float) -> None:
    spread = frame["balancing_spread_eur_mwh"]
    valid = spread.notna()
    candidates = [frame.head(2), frame.tail(2)]
    candidates.append(frame.loc[~valid])
    candidates.append(frame.loc[spread.eq(0)].head(2))
    for boundary in (delta, -delta):
        closest = (spread - boundary).abs().loc[valid].nsmallest(2).index
        candidates.append(frame.loc[closest])
    sample = pd.concat(candidates).drop_duplicates("delivery_start_utc").sort_values(
        "delivery_start_utc"
    )
    columns = [
        "delivery_start_utc",
        "delivery_start_local",
        "local_hour_occurrence",
        "price_area",
        "spot_price_eur_mwh",
        "imbalance_price_eur_mwh",
        "balancing_spread_eur_mwh",
        "absolute_spread_eur_mwh",
        "neutral_band_delta_eur_mwh",
        "target_label",
        "target_is_valid",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample[columns].to_csv(output_path, index=False)


def write_markdown_reports(
    evidence_dir: Path,
    spread_report: dict[str, Any],
    delta_report: dict[str, Any],
    label_report: dict[str, Any],
    baselines: dict[str, Any],
    quality: dict[str, Any],
) -> None:
    distribution = baselines["development_base_rates"]
    counts = distribution["counts"]
    shares = distribution["shares"]
    persistence = baselines["persistence"]
    text = f"""# P3 Target Construction Evidence

**Status:** PASS — P3.1 through P3.4 completed on {RUN_DATE}
**Holdout:** LOCKED AND UNUSED

## Frozen target

`balancing_spread_eur_mwh = imbalance_price_eur_mwh - spot_price_eur_mwh`

- Same DK1 delivery hour and EUR/MWh unit on both sides
- Valid spreads: `{spread_report['valid_spreads']:,}`
- Missing spreads: `{spread_report['missing_spreads']}`
- Preserved missing outcome: `{EXPECTED_BALANCING_GAP.isoformat()}`

## Frozen neutral band

- Rule: Q25 of nonzero absolute development spreads
- Eligible observations: `{delta_report['nonzero_absolute_spreads']:,}`
- Excluded observed-zero spreads: `{delta_report['zero_spreads_excluded']:,}`
- Method: linear interpolation
- Frozen delta: `{delta_report['delta_eur_mwh']:.7f} EUR/MWh`

## Development labels

| Label | Count | Share of valid labels |
|---|---:|---:|
| UP | {counts['UP']:,} | {shares['UP']:.2%} |
| DOWN | {counts['DOWN']:,} | {shares['DOWN']:.2%} |
| NEUTRAL | {counts['NEUTRAL']:,} | {shares['NEUTRAL']:.2%} |

The single missing spread has no label. Observed zero spreads and both exact
boundaries belong to NEUTRAL. No missing value is converted to zero.

## Baselines

- Development-wide descriptive majority: `{baselines['majority_class']['development_wide_descriptive_majority']}`
- Majority descriptive accuracy: `{baselines['majority_class']['development_wide_descriptive_accuracy']:.2%}`
- Ex-post persistence eligible pairs: `{persistence['eligible_pairs']:,}`
- Ex-post persistence descriptive accuracy: `{persistence['development_wide_descriptive_accuracy']:.2%}`
- Persistence remains an ex-post reference because the historical publication
  delay of the preceding balancing outcome is undocumented.
- An availability-safe hour-of-week training-majority reference is registered
  before evaluation. It must be fit independently inside each future training
  segment.

These are in-sample descriptive facts, not evidence of a predictive edge or
executable trading performance.

## Quality gate

- Target rows: `{quality['rows']:,}`
- Target columns: `{quality['columns']}`
- Critical checks passed: `{sum(quality['critical_checks'].values())}/{len(quality['critical_checks'])}`
- Holdout rows: `0`
"""
    (evidence_dir / "README.md").write_text(text, encoding="utf-8")

    baseline_md = f"""# P3.4 Development Base Rates and Baselines

**Status:** {baselines['status']}
**Scope:** development only; all reported accuracies are descriptive/in-sample

| Label | Count | Share |
|---|---:|---:|
| UP | {counts['UP']:,} | {shares['UP']:.6%} |
| DOWN | {counts['DOWN']:,} | {shares['DOWN']:.6%} |
| NEUTRAL | {counts['NEUTRAL']:,} | {shares['NEUTRAL']:.6%} |

The majority baseline must be learned only from the training portion available
for each evaluation. Across the complete development sample, NEUTRAL is the
descriptive majority and represents `{baselines['majority_class']['development_wide_descriptive_accuracy']:.6%}`
of valid labels.

The frozen persistence formula is `y_hat_t = y_(t-1)`. It is computable on
`{persistence['eligible_pairs']:,}` consecutive valid development pairs and has
a descriptive accuracy of `{persistence['development_wide_descriptive_accuracy']:.6%}`.
It is retained only as an ex-post reference because the source does not prove
that the preceding outcome was published by the decision cutoff.

The registered availability-safe supplement is an hour-of-week training
majority: learn a class separately for each Danish local weekday-hour from the
training segment and use the global training majority for unseen groups. Its
performance will be evaluated only inside later chronological splits.
"""
    (evidence_dir / f"p3_4_base_rate_and_baselines_{RUN_DATE}.md").write_text(
        baseline_md, encoding="utf-8"
    )


def validate_and_report(
    repo_root: Path,
    config: dict[str, Any],
    input_path: Path,
    frame: pd.DataFrame,
    delta_audit: dict[str, Any],
    baselines: dict[str, Any],
    output_path: Path,
    evidence_dir: Path,
) -> dict[str, Any]:
    spread = frame["balancing_spread_eur_mwh"]
    valid = spread.notna()
    expected_spread = (
        frame["imbalance_price_eur_mwh"] - frame["spot_price_eur_mwh"]
    )
    configured_delta = float(config["neutral_band"]["numerical_delta"])
    missing_hours = frame.loc[~valid, "delivery_start_utc"].tolist()
    distribution = baselines["development_base_rates"]
    class_total = sum(distribution["counts"].values())
    holdout_start = pd.Timestamp(
        config["periods"]["holdout"]["start_date"],
        tz=config["periods"]["boundary_timezone"],
    ).tz_convert("UTC")
    critical_checks = {
        "input_hash_matches_frozen_p2": sha256(input_path)
        == config["neutral_band"]["input_sha256"],
        "target_rows_equal_p2": len(frame) == EXPECTED_ROWS,
        "target_key_unique": frame["delivery_start_utc"].is_unique,
        "no_holdout_rows": bool(frame["delivery_start_utc"].lt(holdout_start).all()),
        "spread_formula_exact": bool(
            np.isclose(
                spread.loc[valid],
                expected_spread.loc[valid],
                rtol=0,
                atol=1e-12,
            ).all()
        ),
        "only_documented_spread_gap": missing_hours == [EXPECTED_BALANCING_GAP],
        "delta_matches_frozen_config": math.isclose(
            delta_audit["delta_eur_mwh"], configured_delta, rel_tol=0, abs_tol=1e-12
        ),
        "delta_uses_nonzero_development_population": delta_audit[
            "nonzero_absolute_spreads"
        ]
        == 15_392,
        "valid_labels_are_exhaustive": class_total == int(valid.sum()),
        "missing_spread_has_missing_label": bool(
            frame.loc[~valid, "target_label"].isna().all()
        ),
        "zero_spreads_are_neutral": bool(
            frame.loc[spread.eq(0), "target_label"].eq("NEUTRAL").all()
        ),
        "label_values_are_frozen_set": set(frame["target_label"].dropna().unique())
        == set(LABEL_ORDER),
        "persistence_not_decision_eligible": baselines["persistence"][
            "decision_feature_eligible"
        ]
        is False,
    }
    quality = {
        "step": "P3.1-P3.4",
        "status": "PASS" if all(critical_checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "input_file": str(input_path.relative_to(repo_root)),
        "input_sha256": sha256(input_path),
        "output_file": str(output_path.relative_to(repo_root)),
        "output_sha256": sha256(output_path),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "critical_checks": critical_checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        failed = [name for name, passed in critical_checks.items() if not passed]
        raise ValueError(f"P3 quality gate failed: {failed}")
    return quality


def run(repo_root: Path) -> dict[str, Any]:
    config, p2, input_path = load_inputs(repo_root)
    evidence_dir = repo_root / "research/evidence/p3_target_construction"
    output_path = repo_root / "data/processed/p3/target_development.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    target = build_spread(p2)
    delta_audit = calculate_delta(target["balancing_spread_eur_mwh"])
    configured_delta = float(config["neutral_band"]["numerical_delta"])
    if not math.isclose(
        delta_audit["delta_eur_mwh"], configured_delta, rel_tol=0, abs_tol=1e-12
    ):
        raise ValueError(
            "Computed development delta does not match the frozen research config."
        )
    target = assign_labels(target, configured_delta)
    target.to_parquet(output_path, index=False)

    spread = target["balancing_spread_eur_mwh"]
    spread_report = {
        "step": "P3.1",
        "status": "PASS",
        "formula": "ImbalancePriceEUR - SpotPriceEUR",
        "normalized_formula": "imbalance_price_eur_mwh - spot_price_eur_mwh",
        "zone": "DK1",
        "unit": "EUR/MWh",
        "join_key": ["delivery_start_utc", "price_area"],
        "rows": int(len(target)),
        "valid_spreads": int(spread.notna().sum()),
        "missing_spreads": int(spread.isna().sum()),
        "zero_spreads": int(spread.eq(0).sum()),
        "positive_spreads": int(spread.gt(0).sum()),
        "negative_spreads": int(spread.lt(0).sum()),
        "minimum": float(spread.min()),
        "median": float(spread.median()),
        "maximum": float(spread.max()),
        "missing_delivery_hours_utc": [
            value.isoformat()
            for value in target.loc[spread.isna(), "delivery_start_utc"]
        ],
        "interpretation": "Realized balancing pressure relative to the already-cleared day-ahead reference; not executable trading P&L.",
        "holdout": "LOCKED_AND_UNUSED",
    }
    delta_report = {
        "step": "P3.2",
        "status": "FROZEN",
        "frozen_at_utc": config["neutral_band"]["frozen_at_utc"],
        "development_period": config["periods"]["development"],
        "input_file": str(input_path.relative_to(repo_root)),
        "input_sha256": sha256(input_path),
        **delta_audit,
        "configured_delta_eur_mwh": configured_delta,
        "holdout_influenced": False,
        "sensitivity_policy": "Q20 and Q30 may be reported later as secondary Level C sensitivities; Q25 remains primary.",
    }
    distribution = class_distribution(target["target_label"])
    label_report = {
        "step": "P3.3",
        "status": "PASS",
        "rules": {
            "UP": f"spread > {configured_delta}",
            "DOWN": f"spread < -{configured_delta}",
            "NEUTRAL": f"abs(spread) <= {configured_delta}",
            "MISSING": "spread is null -> target label is null",
        },
        "boundary_policy": "Both +delta and -delta are inclusive NEUTRAL boundaries.",
        "observed_zero_policy": "Observed zero spread is NEUTRAL.",
        "missing_policy": "Missing source price remains a missing spread and missing label; never zero-filled.",
        **distribution,
        "holdout": "LOCKED_AND_UNUSED",
    }
    baselines = baseline_report(target)

    json_dump(evidence_dir / f"p3_1_spread_validation_{RUN_DATE}.json", spread_report)
    json_dump(evidence_dir / f"p3_2_delta_freeze_{RUN_DATE}.json", delta_report)
    json_dump(evidence_dir / f"p3_3_label_validation_{RUN_DATE}.json", label_report)
    json_dump(
        evidence_dir / f"p3_4_base_rate_and_baselines_{RUN_DATE}.json", baselines
    )
    audit_sample(
        target,
        evidence_dir / f"target_audit_sample_{RUN_DATE}.csv",
        configured_delta,
    )
    quality = validate_and_report(
        repo_root,
        config,
        input_path,
        target,
        delta_audit,
        baselines,
        output_path,
        evidence_dir,
    )
    write_markdown_reports(
        evidence_dir,
        spread_report,
        delta_report,
        label_report,
        baselines,
        quality,
    )
    return {
        "quality": quality,
        "spread": spread_report,
        "delta": delta_report,
        "labels": label_report,
        "baselines": baselines,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = run(args.repo_root.resolve())
    print(
        json.dumps(
            {
                "status": report["quality"]["status"],
                "rows": report["quality"]["rows"],
                "delta_eur_mwh": report["delta"]["delta_eur_mwh"],
                "class_counts": report["labels"]["counts"],
                "holdout": report["quality"]["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
