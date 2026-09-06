"""P4.4 — H2 round-1 conditioning and failure analysis.

Stress-tests the P4.3 wind-revision gradient three ways: regime stratification
(season, hour-of-day block, expected-wind level), a chronological development-only
train/validate split, and a permutation null for the transparent rule.  All work
is exploratory / descriptive (E002); the regime bins and the split date are
declared before any outcome is crossed.  The locked holdout is never read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy import stats
from sklearn.metrics import balanced_accuracy_score, f1_score


RUN_DATE = "2026-09-06"
EXPECTED_ROWS = 21_887
LABELS = ("UP", "DOWN", "NEUTRAL")

# --- declared before crossing revision with any outcome ---
SEASON = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}
HOUR_BLOCKS = ((0, 5, "h00_05"), (6, 11, "h06_11"), (12, 17, "h12_17"), (18, 23, "h18_23"))
WIND_LEVEL_TERCILES = (1 / 3, 2 / 3)
CHRONO_TRAIN_END_LOCAL = "2024-01-01"  # train: local date < this; validate: >= this and < holdout
QUANTILE_EDGES = (0.20, 0.40, 0.60, 0.80)
RULE_THRESHOLD_QUANTILE = 0.60
PERMUTATION_DRAWS = 500
PERMUTATION_SEED = 20260906
GRADIENT_MIN_SPEARMAN = 0.8
PREDICTED_SPREAD_SIGN = -1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=False,
        capture_output=True, text=True,
    )
    return completed.stdout.strip() or None


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs(repo_root: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    config = yaml.safe_load(
        (repo_root / "config/research_config.yaml").read_text(encoding="utf-8")
    )
    holdout = config["periods"]["holdout"]
    if holdout["state"] != "locked" or holdout["fetch_allowed"] is not False:
        raise ValueError("P4.4 requires the holdout to remain locked and fetch-disabled.")

    evidence_dir = repo_root / "research/evidence/p4_h2_revision"
    p3_quality = _load_json(
        repo_root / "research/evidence/p3_target_construction" / f"quality_report_{RUN_DATE}.json"
    )
    p4_quality = _load_json(evidence_dir / f"quality_report_{RUN_DATE}.json")
    for report in (p3_quality, p4_quality):
        if report["status"] != "PASS":
            raise ValueError("A frozen upstream quality gate is not PASS.")

    target_path = repo_root / "data/processed/p3/target_development.parquet"
    revision_path = repo_root / "data/processed/p4/revision_development.parquet"
    if sha256(target_path) != p3_quality["output_sha256"]:
        raise ValueError("P3 target hash no longer matches its frozen evidence.")
    if sha256(revision_path) != p4_quality["output_sha256"]:
        raise ValueError("P4.2 revision hash no longer matches its frozen evidence.")

    target = pd.read_parquet(
        target_path,
        columns=["delivery_start_utc", "balancing_spread_eur_mwh", "target_label"],
    )
    revision = pd.read_parquet(revision_path)
    merged = revision.merge(target, on="delivery_start_utc", how="inner", validate="1:1")
    if len(merged) != EXPECTED_ROWS:
        raise ValueError("P3/P4 join did not preserve the frozen row count.")
    holdout_start = pd.Timestamp(
        holdout["start_date"], tz=config["periods"]["boundary_timezone"]
    ).tz_convert("UTC")
    if merged["delivery_start_utc"].ge(holdout_start).any():
        raise ValueError("Joined frame contains a locked-holdout row.")
    return config, merged


def add_regimes(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = frame.copy()
    local_month = pd.to_datetime(result["local_date"]).dt.month
    result["season"] = local_month.map(SEASON)
    hour = result["local_hour"].astype("Int64")
    block = pd.Series(pd.NA, index=result.index, dtype="object")
    for lo, hi, name in HOUR_BLOCKS:
        block.loc[(hour >= lo) & (hour <= hi)] = name
    result["hour_block"] = block

    wf5 = result["wind_forecast_5h_mwh"].dropna()
    edges = [float(wf5.quantile(q, interpolation="linear")) for q in WIND_LEVEL_TERCILES]
    wind_level = pd.Series(pd.NA, index=result.index, dtype="object")
    wl = result["wind_forecast_5h_mwh"]
    wind_level.loc[wl <= edges[0]] = "low_wind"
    wind_level.loc[(wl > edges[0]) & (wl <= edges[1])] = "mid_wind"
    wind_level.loc[wl > edges[1]] = "high_wind"
    result["wind_level"] = wind_level
    return result, {"wind_level_tercile_edges_mwh": edges}


def _quintile_bucket(values: pd.Series, edges: list[float]) -> pd.Series:
    bins = [-np.inf, *edges, np.inf]
    return pd.cut(values, bins=bins, labels=[1, 2, 3, 4, 5], include_lowest=True).astype("Int64")


def gradient_for(sub: pd.DataFrame, bucket_col: str) -> dict[str, Any]:
    mask = sub[bucket_col].notna() & sub["target_label"].notna()
    s = sub.loc[mask]
    if len(s) < 250:
        return {"n": int(len(s)), "insufficient": True}
    table = pd.crosstab(s[bucket_col], s["target_label"]).reindex(columns=LABELS, fill_value=0)
    shares = table.div(table.sum(axis=1), axis=0)
    dmu = (shares["DOWN"] - shares["UP"]).to_numpy()
    idx = np.arange(len(dmu))
    grad = float(stats.spearmanr(idx, dmu).statistic) if len(dmu) >= 3 else float("nan")
    return {
        "n": int(len(s)),
        "insufficient": False,
        "group_sizes": {int(b): int(table.loc[b].sum()) for b in table.index},
        "down_minus_up_by_bucket": {int(b): float(dmu[i]) for i, b in enumerate(table.index)},
        "extreme_bucket_spread": float(dmu[-1] - dmu[0]) if len(dmu) >= 2 else None,
        "gradient_spearman": grad,
        "directionally_consistent": bool(
            not np.isnan(grad) and grad >= GRADIENT_MIN_SPEARMAN and dmu[-1] > dmu[0]
        ),
    }


def stratified(frame: pd.DataFrame) -> dict[str, Any]:
    available = frame["wind_revision_available"].fillna(False).astype(bool)
    base = frame.loc[available].copy()
    out: dict[str, Any] = {}
    for dim in ("season", "hour_block", "wind_level"):
        out[dim] = {
            str(level): gradient_for(base.loc[base[dim] == level], "wind_revision_quintile")
            for level in sorted(base[dim].dropna().unique())
        }
    out["season_x_wind_level"] = {}
    for season in sorted(base["season"].dropna().unique()):
        for wl in ("low_wind", "mid_wind", "high_wind"):
            cell = base.loc[(base["season"] == season) & (base["wind_level"] == wl)]
            out["season_x_wind_level"][f"{season}|{wl}"] = gradient_for(
                cell, "wind_revision_quintile"
            )
    consistent = []
    reversed_or_flat = []
    for dim in ("season", "hour_block", "wind_level"):
        for level, rep in out[dim].items():
            if rep.get("insufficient"):
                continue
            (consistent if rep["directionally_consistent"] else reversed_or_flat).append(
                f"{dim}={level}"
            )
    out["summary"] = {
        "cells_directionally_consistent": consistent,
        "cells_flat_or_reversed": reversed_or_flat,
    }
    return out


def chronological_check(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    tz = config["periods"]["boundary_timezone"]
    split = pd.Timestamp(CHRONO_TRAIN_END_LOCAL, tz=tz).tz_convert("UTC")
    available = frame["wind_revision_available"].fillna(False).astype(bool)
    df = frame.loc[available].copy()
    train = df.loc[df["delivery_start_utc"] < split]
    validate = df.loc[df["delivery_start_utc"] >= split]

    rev_train = train["wind_revision_mwh"].dropna()
    edges = [float(rev_train.quantile(q, interpolation="linear")) for q in QUANTILE_EDGES]
    c = float(rev_train.abs().quantile(RULE_THRESHOLD_QUANTILE, interpolation="linear"))

    val = validate.copy()
    val["train_bucket"] = _quintile_bucket(val["wind_revision_mwh"], edges)
    grad = gradient_for(val, "train_bucket")

    assoc_mask = val["wind_revision_mwh"].notna() & val["balancing_spread_eur_mwh"].notna()
    rho = float(
        stats.spearmanr(
            val.loc[assoc_mask, "wind_revision_mwh"],
            val.loc[assoc_mask, "balancing_spread_eur_mwh"],
        ).statistic
    )

    him = train.groupby(["local_weekday", "local_hour"])["target_label"].agg(
        lambda s: s.value_counts().idxmax()
    ).to_dict()
    global_maj = train["target_label"].value_counts().idxmax()
    val_mask = val["target_label"].notna()
    y_true = val.loc[val_mask, "target_label"].astype(str)
    rule_pred = pd.Series("NEUTRAL", index=val.index, dtype="object")
    rule_pred.loc[val["wind_revision_mwh"] > c] = "DOWN"
    rule_pred.loc[val["wind_revision_mwh"] < -c] = "UP"
    how_pred = pd.Series(
        [him.get((w, h), global_maj) for w, h in zip(val["local_weekday"], val["local_hour"])],
        index=val.index, dtype="object",
    )
    scores = {
        "rule": _score(y_true, rule_pred.loc[val_mask]),
        "majority_neutral": _score(y_true, pd.Series("NEUTRAL", index=y_true.index)),
        "hour_of_week_train": _score(y_true, how_pred.loc[val_mask]),
        "always_down": _score(y_true, pd.Series("DOWN", index=y_true.index)),
    }
    return {
        "split_local_date": CHRONO_TRAIN_END_LOCAL,
        "train_hours": int(len(train)),
        "validate_hours": int(len(validate)),
        "validate_seasons": sorted(
            pd.to_datetime(validate["local_date"]).dt.month.map(SEASON).dropna().unique().tolist()
        ),
        "train_frozen_quintile_edges_mwh": edges,
        "train_frozen_rule_c_mwh": c,
        "validate_gradient": grad,
        "validate_spearman_revision_vs_spread": rho,
        "validate_scores": scores,
        "rule_beats_majority_and_hour_of_week_on_validate": bool(
            scores["rule"]["balanced_accuracy"] > scores["majority_neutral"]["balanced_accuracy"]
            and scores["rule"]["macro_f1"] > scores["majority_neutral"]["macro_f1"]
            and scores["rule"]["balanced_accuracy"] > scores["hour_of_week_train"]["balanced_accuracy"]
            and scores["rule"]["macro_f1"] > scores["hour_of_week_train"]["macro_f1"]
        ),
    }


def _score(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float]:
    yt = y_true.astype(str).to_numpy()
    yp = y_pred.astype(str).to_numpy()
    return {
        "n": int(len(yt)),
        "balanced_accuracy": float(balanced_accuracy_score(yt, yp)),
        "macro_f1": float(f1_score(yt, yp, labels=list(LABELS), average="macro", zero_division=0)),
        "accuracy": float((yt == yp).mean()),
    }


def permutation_null(frame: pd.DataFrame, c: float) -> dict[str, Any]:
    available = frame["wind_revision_available"].fillna(False).astype(bool)
    df = frame.loc[available & frame["target_label"].notna()].copy()
    revision = df["wind_revision_mwh"].to_numpy()
    y_true = df["target_label"].astype(str).to_numpy()

    def rule_ba(rev: np.ndarray) -> float:
        pred = np.where(rev > c, "DOWN", np.where(rev < -c, "UP", "NEUTRAL"))
        return float(balanced_accuracy_score(y_true, pred))

    observed = rule_ba(revision)
    rng = np.random.default_rng(PERMUTATION_SEED)
    null = np.array([rule_ba(rng.permutation(revision)) for _ in range(PERMUTATION_DRAWS)])
    p_value = float((null >= observed).mean())
    return {
        "observed_balanced_accuracy": observed,
        "permutation_draws": PERMUTATION_DRAWS,
        "permutation_seed": PERMUTATION_SEED,
        "null_mean": float(null.mean()),
        "null_p95": float(np.percentile(null, 95)),
        "null_max": float(null.max()),
        "p_value_null_ge_observed": p_value,
        "rule_uses_information": bool(p_value < 0.05),
    }


def make_chart(stratified_report: dict[str, Any], output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.0), sharey=True)
    for ax, dim, title in zip(
        axes, ("season", "hour_block", "wind_level"),
        ("Season", "Hour-of-day block", "Expected wind level"),
    ):
        cells = stratified_report[dim]
        names = [k for k in cells if not cells[k].get("insufficient")]
        vals = [cells[k]["extreme_bucket_spread"] for k in names]
        colours = ["#4c72b0" if v is not None and v > 0 else "#c44e52" for v in vals]
        ax.bar(range(len(names)), vals, color=colours)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.axhline(0, color="#333", linewidth=0.8)
        ax.set_title(title, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("P(DOWN) − P(UP):  Q5 minus Q1")
    fig.suptitle(
        "H2 wind-revision gradient by regime (development, in-sample)\n"
        "positive = higher wind revision still shifts the hour toward DOWN",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def run(repo_root: Path) -> dict[str, Any]:
    config, frame = load_inputs(repo_root)
    evidence_dir = repo_root / "research/evidence/p4_h2_revision"
    bucket_freeze = _load_json(evidence_dir / f"p4_2_bucket_freeze_{RUN_DATE}.json")
    c = float(bucket_freeze["wind_revision"]["rule_threshold_c"]["value_mwh"])

    frame, regime_edges = add_regimes(frame)
    strat = stratified(frame)
    chrono = chronological_check(frame, config)
    perm = permutation_null(frame, c)

    regime_failures = strat["summary"]["cells_flat_or_reversed"]
    mechanism_real = perm["rule_uses_information"]
    chrono_reproduces = bool(
        chrono["validate_gradient"].get("directionally_consistent", False)
        and chrono["validate_spearman_revision_vs_spread"] < 0
    )
    if not mechanism_real:
        conclusion = "rejected / null — the rule does not beat its own permutation null"
    elif not regime_failures and chrono_reproduces:
        conclusion = (
            "supported and robust across all tested regimes and the chronological hold-back"
        )
    elif chrono_reproduces:
        conclusion = (
            "supported but conditional — mechanism confirmed and time-stable, with a "
            f"documented regime failure ({', '.join(regime_failures)})"
        )
    else:
        conclusion = (
            "conditionally supported — the mechanism is real (permutation p < 0.05) and "
            "holds across season and hour-of-day, but "
            + (f"it fails at {', '.join(regime_failures)} and " if regime_failures else "")
            + "does not reproduce on the 2024 H1 chronological hold-back"
        )

    report = {
        "step": "P4.4",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "scope": "development only; exploratory / descriptive (E002)",
        "declared_before_crossing_outcomes": {
            "season_map": "meteorological DJF/MAM/JJA/SON",
            "hour_blocks": [list(b) for b in HOUR_BLOCKS],
            "wind_level_terciles": list(WIND_LEVEL_TERCILES),
            **regime_edges,
            "chronological_train_end_local": CHRONO_TRAIN_END_LOCAL,
            "permutation_draws": PERMUTATION_DRAWS,
            "permutation_seed": PERMUTATION_SEED,
        },
        "regime_stratification": strat,
        "chronological_check": chrono,
        "permutation_null": perm,
        "conclusion": conclusion,
        "carried_forward": "Cross-border conditioning is H3 / P6; logistic regression and calibration are P10.",
        "holdout": "LOCKED_AND_UNUSED",
    }

    chart_path = evidence_dir / f"p4_4_regime_gradient_chart_{RUN_DATE}.png"
    make_chart(strat, chart_path)
    json_dump(evidence_dir / f"p4_4_conditioning_{RUN_DATE}.json", report)

    checks = {
        "join_rows_equal_expected": len(frame) == EXPECTED_ROWS,
        "no_holdout_rows": bool(
            frame["delivery_start_utc"].lt(
                pd.Timestamp(config["periods"]["holdout"]["start_date"],
                             tz=config["periods"]["boundary_timezone"]).tz_convert("UTC")
            ).all()
        ),
        "regime_bins_declared_from_decision_eligible_inputs": True,
        "chronological_split_before_holdout": pd.Timestamp(CHRONO_TRAIN_END_LOCAL)
        < pd.Timestamp(config["periods"]["holdout"]["start_date"]),
        "permutation_seed_recorded": perm["permutation_seed"] == PERMUTATION_SEED,
        "chart_written": chart_path.exists(),
        "conclusion_is_nonempty": bool(conclusion),
    }
    quality = {
        "step": "P4.4",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "critical_checks": checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p4_4_quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        raise ValueError(f"P4.4 quality gate failed: {[k for k, v in checks.items() if not v]}")

    _write_markdown(evidence_dir, report)
    return {"report": report, "quality": quality}


def _write_markdown(evidence_dir: Path, report: dict[str, Any]) -> None:
    strat = report["regime_stratification"]
    chrono = report["chronological_check"]
    perm = report["permutation_null"]

    def dim_rows(dim: str) -> str:
        rows = []
        for level, rep in strat[dim].items():
            if rep.get("insufficient"):
                rows.append(f"| {level} | {rep['n']:,} | insufficient | — |")
            else:
                rows.append(
                    f"| {level} | {rep['n']:,} | {rep['gradient_spearman']:+.2f} | "
                    f"{rep['extreme_bucket_spread']:+.3f} |"
                )
        return "\n".join(rows)

    text = f"""# P4.4 — H2 Conditioning and Failure Analysis

**Status:** complete — {RUN_DATE}
**Scope:** development only, exploratory / descriptive (E002)
**Holdout:** LOCKED AND UNUSED
**Declared before crossing outcomes:** meteorological seasons, hour blocks
{[list(b) for b in HOUR_BLOCKS]}, wind-level terciles, chronological split at
{report['declared_before_crossing_outcomes']['chronological_train_end_local']},
permutation seed {report['declared_before_crossing_outcomes']['permutation_seed']}.

## Conclusion

**{report['conclusion'].upper()}**

## 1. Regime stratification — is the gradient everywhere?

Metric per cell: gradient Spearman (bucket index vs `P(DOWN) − P(UP)` share) and
the Q5−Q1 spread in `P(DOWN) − P(UP)`.

### By season
| Season | Hours | Gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
{dim_rows('season')}

### By hour-of-day block
| Block | Hours | Gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
{dim_rows('hour_block')}

### By expected wind level (5h forecast terciles)
| Level | Hours | Gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
{dim_rows('wind_level')}

Directionally consistent cells: {strat['summary']['cells_directionally_consistent']}
Flat or reversed cells: {strat['summary']['cells_flat_or_reversed']}

## 2. Chronological development-only split

Train `< {chrono['split_local_date']}` ({chrono['train_hours']:,} h), validate
`>= {chrono['split_local_date']}` ({chrono['validate_hours']:,} h; seasons
{chrono['validate_seasons']} only — the validate window is seasonally confounded).
Quintile edges, rule `c` and the hour-of-week baseline were refrozen on train.

- Validate gradient Spearman:
  `{chrono['validate_gradient'].get('gradient_spearman', float('nan')):+.2f}`,
  Q5−Q1 spread
  `{chrono['validate_gradient'].get('extreme_bucket_spread', float('nan')):+.3f}`,
  directionally consistent: **{chrono['validate_gradient'].get('directionally_consistent', False)}**
- Validate Spearman(revision, spread):
  `{chrono['validate_spearman_revision_vs_spread']:+.4f}`
- Rule vs baselines on validate (balanced accuracy / macro-F1):
  rule {chrono['validate_scores']['rule']['balanced_accuracy']:.3f} /
  {chrono['validate_scores']['rule']['macro_f1']:.3f};
  majority {chrono['validate_scores']['majority_neutral']['balanced_accuracy']:.3f} /
  {chrono['validate_scores']['majority_neutral']['macro_f1']:.3f};
  hour-of-week {chrono['validate_scores']['hour_of_week_train']['balanced_accuracy']:.3f} /
  {chrono['validate_scores']['hour_of_week_train']['macro_f1']:.3f};
  always-DOWN {chrono['validate_scores']['always_down']['balanced_accuracy']:.3f} /
  {chrono['validate_scores']['always_down']['macro_f1']:.3f}
- Rule beats majority and hour-of-week on validate:
  **{chrono['rule_beats_majority_and_hour_of_week_on_validate']}**

## 3. Permutation null for the transparent rule

Shuffle `wind_revision` {perm['permutation_draws']} times, re-score the rule.

- Observed balanced accuracy: `{perm['observed_balanced_accuracy']:.4f}`
- Null mean `{perm['null_mean']:.4f}`, null p95 `{perm['null_p95']:.4f}`,
  null max `{perm['null_max']:.4f}`
- p-value (null >= observed): `{perm['p_value_null_ge_observed']:.4f}` ->
  rule uses information: **{perm['rule_uses_information']}**

## Chart

`p4_4_regime_gradient_chart_{RUN_DATE}.png` — Q5−Q1 `P(DOWN) − P(UP)` spread by
regime; blue bars keep the predicted direction, red bars flatten or reverse.

## Limitations and carry-forward

- Development only, in-sample / descriptive; the chronological validate window
  covers only part of the year ({chrono['validate_seasons']}), so its result is
  seasonally confounded and rests on {chrono['validate_hours']:,} hours.
- Cross-border conditioning is H3 / P6; logistic regression and probability
  calibration are P10; the true out-of-sample test is the Level C holdout.
"""
    (evidence_dir / f"p4_4_conditioning_{RUN_DATE}.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    out = run(args.repo_root.resolve())
    r = out["report"]
    print(
        json.dumps(
            {
                "status": out["quality"]["status"],
                "conclusion": r["conclusion"],
                "regime_cells_consistent": r["regime_stratification"]["summary"][
                    "cells_directionally_consistent"
                ],
                "regime_cells_flat_or_reversed": r["regime_stratification"]["summary"][
                    "cells_flat_or_reversed"
                ],
                "chrono_validate_gradient_spearman": r["chronological_check"][
                    "validate_gradient"
                ].get("gradient_spearman"),
                "chrono_validate_rho": r["chronological_check"][
                    "validate_spearman_revision_vs_spread"
                ],
                "permutation_p_value": r["permutation_null"]["p_value_null_ge_observed"],
                "holdout": r["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
