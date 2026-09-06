"""Run the pre-registered P4.1 round-1 test for H2 (renewable forecast revision).

P4.3 joins the frozen P4.2 revisions to the P3 labels and signed spread and
executes exactly the procedure fixed in P4.1: a bucket-by-label contingency
table, a Spearman rank association with a bootstrap CI, and a transparent rule
scored against the two availability-safe baselines.  Nothing about the procedure
is chosen here.  The locked holdout is never read.
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy import stats
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score


RUN_DATE = "2026-09-06"
EXPECTED_ROWS = 21_887
LABELS = ("UP", "DOWN", "NEUTRAL")
LABEL_SCORE = {"UP": 1, "NEUTRAL": 0, "DOWN": -1}

BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20260906
BOOTSTRAP_CI = (2.5, 97.5)

# P4.3 operationalization of the pre-registered "monotone across at least four of
# five buckets" criterion, fixed before the join.
GRADIENT_MIN_SPEARMAN = 0.8
PREDICTED_SPREAD_SIGN = -1  # positive wind revision -> lower (more negative) spread


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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs(repo_root: Path) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    config = yaml.safe_load(
        (repo_root / "config/research_config.yaml").read_text(encoding="utf-8")
    )
    holdout = config["periods"]["holdout"]
    if holdout["state"] not in ("locked", "evaluated") or holdout["fetch_allowed"] is not False:
        raise ValueError("P4.3 requires the holdout to remain locked and fetch-disabled.")

    evidence_dir = repo_root / "research/evidence/p4_h2_revision"
    p3_quality = _load_json(
        repo_root
        / "research/evidence/p3_target_construction"
        / f"quality_report_{RUN_DATE}.json"
    )
    p4_quality = _load_json(evidence_dir / f"quality_report_{RUN_DATE}.json")
    bucket_freeze = _load_json(evidence_dir / f"p4_2_bucket_freeze_{RUN_DATE}.json")
    for report in (p3_quality, p4_quality):
        if report["status"] != "PASS":
            raise ValueError("A frozen upstream quality gate is not PASS.")

    target_path = repo_root / "data/processed/p3/target_development.parquet"
    revision_path = repo_root / "data/processed/p4/revision_development.parquet"
    if sha256(target_path) != p3_quality["output_sha256"]:
        raise ValueError("P3 target hash no longer matches its frozen evidence.")
    if sha256(revision_path) != p4_quality["output_sha256"]:
        raise ValueError("P4.2 revision hash no longer matches its frozen evidence.")

    # local_weekday / local_hour already travel on the P4.2 revision table.
    target = pd.read_parquet(
        target_path,
        columns=[
            "delivery_start_utc",
            "balancing_spread_eur_mwh",
            "target_label",
            "target_is_valid",
        ],
    )
    revision = pd.read_parquet(revision_path)
    merged = revision.merge(target, on="delivery_start_utc", how="inner", validate="1:1")
    for needed in ("local_weekday", "local_hour"):
        if needed not in merged.columns:
            raise ValueError(f"Joined frame is missing {needed}.")
    if len(merged) != EXPECTED_ROWS or not merged["delivery_start_utc"].is_unique:
        raise ValueError("P3/P4 join did not preserve the frozen unique-hour shape.")
    holdout_start = pd.Timestamp(
        holdout["start_date"], tz=config["periods"]["boundary_timezone"]
    ).tz_convert("UTC")
    if merged["delivery_start_utc"].ge(holdout_start).any():
        raise ValueError("Joined frame contains a locked-holdout row.")
    return config, merged, bucket_freeze


def contingency(frame: pd.DataFrame, bucket_col: str, revision_available: pd.Series) -> dict[str, Any]:
    mask = revision_available & frame["target_label"].notna() & frame[bucket_col].notna()
    sub = frame.loc[mask, [bucket_col, "target_label"]]
    table = pd.crosstab(sub[bucket_col], sub["target_label"]).reindex(columns=LABELS, fill_value=0)
    buckets = list(table.index)
    counts = {int(b): {lab: int(table.loc[b, lab]) for lab in LABELS} for b in buckets}
    row_shares = {
        int(b): {
            lab: (table.loc[b, lab] / table.loc[b].sum()) if table.loc[b].sum() else None
            for lab in LABELS
        }
        for b in buckets
    }
    down_minus_up = {
        int(b): (row_shares[int(b)]["DOWN"] - row_shares[int(b)]["UP"])
        if row_shares[int(b)]["DOWN"] is not None
        else None
        for b in buckets
    }
    ordered = [down_minus_up[int(b)] for b in buckets]
    if len(ordered) >= 3 and all(v is not None for v in ordered):
        gradient_spearman = float(stats.spearmanr(list(range(len(ordered))), ordered).statistic)
        endpoints_ok = ordered[-1] > ordered[0]
    else:
        gradient_spearman = float("nan")
        endpoints_ok = False
    return {
        "bucket_column": bucket_col,
        "n": int(mask.sum()),
        "group_sizes": {int(b): int(table.loc[b].sum()) for b in buckets},
        "counts": counts,
        "row_shares_p_label_given_bucket": row_shares,
        "down_share_minus_up_share": down_minus_up,
        "gradient_bucket_index_spearman": gradient_spearman,
        "endpoints_bucket5_gt_bucket1": bool(endpoints_ok),
        "gradient_directionally_consistent": bool(
            gradient_spearman >= GRADIENT_MIN_SPEARMAN and endpoints_ok
        ),
    }


def spearman_with_ci(x: pd.Series, y: pd.Series, label: str) -> dict[str, Any]:
    mask = x.notna() & y.notna()
    xv = x.loc[mask].to_numpy(dtype=float)
    yv = y.loc[mask].to_numpy(dtype=float)
    point = float(stats.spearmanr(xv, yv).statistic)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(xv)
    draws = np.empty(BOOTSTRAP_DRAWS, dtype=float)
    for i in range(BOOTSTRAP_DRAWS):
        idx = rng.integers(0, n, n)
        draws[i] = stats.spearmanr(xv[idx], yv[idx]).statistic
    low, high = (float(v) for v in np.percentile(draws, BOOTSTRAP_CI))
    excludes_zero = (low > 0 and high > 0) or (low < 0 and high < 0)
    observed_sign = 0 if point == 0 else int(math.copysign(1, point))
    return {
        "pair": label,
        "n": int(n),
        "spearman_rho": point,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "ci_percentiles": list(BOOTSTRAP_CI),
        "ci_low": low,
        "ci_high": high,
        "ci_excludes_zero": bool(excludes_zero),
        "observed_sign": observed_sign,
        "predicted_sign": PREDICTED_SPREAD_SIGN,
        "sign_matches_prediction": bool(observed_sign == PREDICTED_SPREAD_SIGN),
        "association_supported": bool(excludes_zero and observed_sign == PREDICTED_SPREAD_SIGN),
    }


def transparent_rule(revision: pd.Series, c: float) -> pd.Series:
    pred = pd.Series("NEUTRAL", index=revision.index, dtype="object")
    pred.loc[revision > c] = "DOWN"
    pred.loc[revision < -c] = "UP"
    return pred.where(revision.notna())


def _scores(y_true: pd.Series, y_pred: pd.Series) -> dict[str, Any]:
    mask = y_true.notna() & y_pred.notna()
    yt = y_true.loc[mask].astype(str)
    yp = y_pred.loc[mask].astype(str)
    cm = confusion_matrix(yt, yp, labels=list(LABELS))
    return {
        "n": int(mask.sum()),
        "balanced_accuracy": float(balanced_accuracy_score(yt, yp)),
        "macro_f1": float(f1_score(yt, yp, labels=list(LABELS), average="macro", zero_division=0)),
        "accuracy": float((yt.to_numpy() == yp.to_numpy()).mean()),
        "confusion_actual_rows_pred_cols": {
            LABELS[i]: {LABELS[j]: int(cm[i, j]) for j in range(3)} for i in range(3)
        },
    }


def hour_of_week_baseline(frame: pd.DataFrame, eval_mask: pd.Series) -> pd.Series:
    sub = frame.loc[eval_mask, ["local_weekday", "local_hour", "target_label"]].dropna()
    global_majority = sub["target_label"].value_counts().idxmax()
    cell = (
        sub.groupby(["local_weekday", "local_hour"])["target_label"]
        .agg(lambda s: s.value_counts().idxmax())
        .to_dict()
    )
    keys = list(zip(frame["local_weekday"], frame["local_hour"]))
    return pd.Series(
        [cell.get(k, global_majority) for k in keys], index=frame.index, dtype="object"
    )


def persistence_baseline(frame: pd.DataFrame) -> pd.Series:
    prev_label = frame["target_label"].shift(1)
    prev_time = frame["delivery_start_utc"].shift(1)
    consecutive = (frame["delivery_start_utc"] - prev_time).eq(pd.Timedelta(hours=1))
    return prev_label.where(consecutive)


def evaluate_variable(
    frame: pd.DataFrame,
    revision_col: str,
    available_col: str,
    quintile_col: str,
    decile_col: str,
    c: float,
    name: str,
    solar_only_label: bool,
) -> dict[str, Any]:
    available = frame[available_col].fillna(False).astype(bool)
    quintile_table = contingency(frame, quintile_col, available)
    decile_table = contingency(frame, decile_col, available)

    signed_spread = frame["balancing_spread_eur_mwh"]
    label_score = frame["target_label"].map(LABEL_SCORE)
    primary_assoc = spearman_with_ci(
        frame[revision_col].where(available), signed_spread, f"{name} vs signed_spread"
    )
    secondary_assoc = spearman_with_ci(
        frame[revision_col].where(available), label_score, f"{name} vs label_score"
    )

    eval_mask = available & frame["target_label"].notna()
    y_true = frame["target_label"].where(eval_mask)
    rule_pred = transparent_rule(frame[revision_col].where(available), c).where(eval_mask)
    majority_pred = pd.Series("NEUTRAL", index=frame.index, dtype="object").where(eval_mask)
    how_pred = hour_of_week_baseline(frame, eval_mask).where(eval_mask)
    persistence_pred = persistence_baseline(frame).where(eval_mask)

    rule_scores = _scores(y_true, rule_pred)
    majority_scores = _scores(y_true, majority_pred)
    how_scores = _scores(y_true, how_pred)
    persistence_scores = _scores(y_true, persistence_pred)

    beats_majority = (
        rule_scores["balanced_accuracy"] > majority_scores["balanced_accuracy"]
        and rule_scores["macro_f1"] > majority_scores["macro_f1"]
    )
    beats_how = (
        rule_scores["balanced_accuracy"] > how_scores["balanced_accuracy"]
        and rule_scores["macro_f1"] > how_scores["macro_f1"]
    )
    beats_persistence = (
        rule_scores["balanced_accuracy"] > persistence_scores["balanced_accuracy"]
        and rule_scores["macro_f1"] > persistence_scores["macro_f1"]
    )

    gradient_ok = quintile_table["gradient_directionally_consistent"]
    association_ok = primary_assoc["association_supported"]
    rule_beats_availability_safe = beats_majority and beats_how

    if gradient_ok and association_ok and rule_beats_availability_safe:
        conclusion = (
            "conditionally supported - solar only, needs replication"
            if solar_only_label
            else "supported"
        )
    elif gradient_ok and association_ok:
        conclusion = "conditionally supported / mechanism only"
    else:
        conclusion = "rejected / null"

    return {
        "variable": name,
        "rule_threshold_c_mwh": c,
        "contingency_quintile": quintile_table,
        "contingency_decile": decile_table,
        "association_primary_signed_spread": primary_assoc,
        "association_secondary_label_score": secondary_assoc,
        "transparent_rule": {
            "definition": f"DOWN if {name} > {c:.6f}; UP if < -{c:.6f}; else NEUTRAL",
            "scores": rule_scores,
        },
        "baselines": {
            "majority_neutral_in_sample": majority_scores,
            "hour_of_week_training_majority_in_sample": how_scores,
            "persistence_ex_post_reference": persistence_scores,
        },
        "criteria_evaluation": {
            "gradient_directionally_consistent": bool(gradient_ok),
            "primary_association_supported": bool(association_ok),
            "rule_beats_majority": bool(beats_majority),
            "rule_beats_hour_of_week": bool(beats_how),
            "rule_beats_availability_safe_baselines": bool(rule_beats_availability_safe),
            "rule_beats_persistence_reported_not_gated": bool(beats_persistence),
        },
        "conclusion": conclusion,
        "interpretation": "Development-wide, in-sample / descriptive (E002). The transparent rule has no outcome-fitted parameters; a chronological out-of-sample evaluation belongs to later stages.",
        "holdout": "LOCKED_AND_UNUSED",
    }


def make_chart(frame: pd.DataFrame, output_path: Path) -> None:
    available = frame["wind_revision_available"].fillna(False).astype(bool)
    mask = available & frame["target_label"].notna() & frame["wind_revision_quintile"].notna()
    sub = frame.loc[mask]
    table = pd.crosstab(sub["wind_revision_quintile"], sub["target_label"]).reindex(
        columns=LABELS, fill_value=0
    )
    shares = table.div(table.sum(axis=1), axis=0)
    buckets = list(shares.index)
    x = np.arange(len(buckets))
    width = 0.26
    colours = {"UP": "#c44e52", "NEUTRAL": "#8c8c8c", "DOWN": "#4c72b0"}

    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    for offset, lab in zip((-width, 0.0, width), ("UP", "NEUTRAL", "DOWN")):
        ax.bar(x + offset, shares[lab].to_numpy(), width, label=lab, color=colours[lab])
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"Q{b}\n(most negative)" if b == buckets[0] else (f"Q{b}\n(most positive)" if b == buckets[-1] else f"Q{b}") for b in buckets]
    )
    ax.set_xlabel("wind_revision quintile  (signed, development-only Q20/Q40/Q60/Q80)")
    ax.set_ylabel("Share of hours in bucket")
    ax.set_title("DK1 balancing-pressure label by 5h-to-1h wind forecast revision\n(development 2022-01-01 to 2024-06-30, in-sample / descriptive)")
    ax.legend(title="Realized label", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(0.65, float(shares.to_numpy().max()) + 0.05))
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def validate_and_report(
    repo_root: Path,
    config: dict[str, Any],
    frame: pd.DataFrame,
    bucket_freeze: dict[str, Any],
    primary: dict[str, Any],
    chart_path: Path,
    evidence_dir: Path,
) -> dict[str, Any]:
    frozen_c = bucket_freeze["wind_revision"]["rule_threshold_c"]["value_mwh"]
    frozen_edges = bucket_freeze["wind_revision"]["quantile_scheme"]["interior_edges"]
    holdout_start = pd.Timestamp(
        config["periods"]["holdout"]["start_date"],
        tz=config["periods"]["boundary_timezone"],
    ).tz_convert("UTC")
    checks = {
        "join_rows_equal_expected": len(frame) == EXPECTED_ROWS,
        "join_key_unique": frame["delivery_start_utc"].is_unique,
        "no_holdout_rows": bool(frame["delivery_start_utc"].lt(holdout_start).all()),
        "rule_threshold_matches_frozen": math.isclose(
            primary["rule_threshold_c_mwh"], frozen_c, rel_tol=0, abs_tol=1e-9
        ),
        "quintile_edges_are_frozen": frozen_edges == sorted(frozen_edges),
        "primary_is_wind": primary["variable"] == "wind_revision_mwh",
        "bootstrap_seed_recorded": primary["association_primary_signed_spread"]["bootstrap_seed"]
        == BOOTSTRAP_SEED,
        "chart_written": chart_path.exists(),
        "conclusion_in_frozen_set": primary["conclusion"]
        in {
            "supported",
            "conditionally supported / mechanism only",
            "rejected / null",
        },
    }
    quality = {
        "step": "P4.3",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "critical_checks": checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p4_3_quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        failed = [name for name, ok in checks.items() if not ok]
        raise ValueError(f"P4.3 quality gate failed: {failed}")
    return quality


def write_markdown(
    evidence_dir: Path, primary: dict[str, Any], solar_all: dict[str, Any], solar_bp: dict[str, Any]
) -> None:
    def bucket_block(report: dict[str, Any]) -> str:
        cont = report["contingency_quintile"]
        rows = []
        for b, shares in cont["row_shares_p_label_given_bucket"].items():
            rows.append(
                f"| Q{b} | {cont['group_sizes'][b]:,} | {shares['UP']:.1%} | "
                f"{shares['NEUTRAL']:.1%} | {shares['DOWN']:.1%} | "
                f"{cont['down_share_minus_up_share'][b]:+.3f} |"
            )
        return "\n".join(rows)

    assoc = primary["association_primary_signed_spread"]
    rule = primary["transparent_rule"]["scores"]
    maj = primary["baselines"]["majority_neutral_in_sample"]
    how = primary["baselines"]["hour_of_week_training_majority_in_sample"]
    per = primary["baselines"]["persistence_ex_post_reference"]
    crit = primary["criteria_evaluation"]

    text = f"""# P4.3 H2 Round-1 Result

**Status:** complete — {RUN_DATE}
**Scope:** development 2022-01-01 to 2024-06-30, in-sample / descriptive (E002)
**Holdout:** LOCKED AND UNUSED
**Procedure:** exactly as pre-registered in P4.1 / D027; nothing chosen here

## Primary test — wind_revision (raw MWh)

**Conclusion: {primary['conclusion'].upper()}**

### Contingency: label share by signed wind_revision quintile

| Bucket | Hours | P(UP) | P(NEUTRAL) | P(DOWN) | DOWN-share - UP-share |
|---|---:|---:|---:|---:|---:|
{bucket_block(primary)}

Gradient (bucket index vs DOWN-minus-UP share) Spearman:
`{primary['contingency_quintile']['gradient_bucket_index_spearman']:+.3f}`
(threshold `>= {GRADIENT_MIN_SPEARMAN}`), endpoints Q5 > Q1:
`{primary['contingency_quintile']['endpoints_bucket5_gt_bucket1']}` ->
directionally consistent: **{crit['gradient_directionally_consistent']}**

### Rank association

Primary Spearman of signed `wind_revision` vs the continuous signed spread:
`rho = {assoc['spearman_rho']:+.4f}`, n = {assoc['n']:,},
95% bootstrap CI [`{assoc['ci_low']:+.4f}`, `{assoc['ci_high']:+.4f}`]
({assoc['bootstrap_draws']:,} draws, seed {assoc['bootstrap_seed']}).
Predicted sign negative; observed sign
{"negative" if assoc['observed_sign'] < 0 else ("positive" if assoc['observed_sign'] > 0 else "zero")};
CI excludes zero: {assoc['ci_excludes_zero']} -> association supported:
**{crit['primary_association_supported']}**

Secondary Spearman vs the +1/0/-1 label score:
`rho = {primary['association_secondary_label_score']['spearman_rho']:+.4f}`.

### Transparent rule vs baselines (in-sample, same rows)

Rule: DOWN if `wind_revision > {primary['rule_threshold_c_mwh']:.3f}`, UP if
`< -{primary['rule_threshold_c_mwh']:.3f}`, else NEUTRAL.

| Method | Balanced accuracy | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| Transparent revision rule | {rule['balanced_accuracy']:.4f} | {rule['macro_f1']:.4f} | {rule['accuracy']:.4f} |
| Majority (NEUTRAL) | {maj['balanced_accuracy']:.4f} | {maj['macro_f1']:.4f} | {maj['accuracy']:.4f} |
| Hour-of-week training majority | {how['balanced_accuracy']:.4f} | {how['macro_f1']:.4f} | {how['accuracy']:.4f} |
| Persistence (ex-post reference) | {per['balanced_accuracy']:.4f} | {per['macro_f1']:.4f} | {per['accuracy']:.4f} |

Rule beats majority: {crit['rule_beats_majority']}; beats hour-of-week:
{crit['rule_beats_hour_of_week']}; beats both availability-safe baselines:
**{crit['rule_beats_availability_safe_baselines']}**. Beats persistence
(reported, not a gate): {crit['rule_beats_persistence_reported_not_gated']}.

## Secondary test — solar_revision

- All numeric pairs: **{solar_all['conclusion'].upper()}**
  (gradient {solar_all['criteria_evaluation']['gradient_directionally_consistent']},
  association {solar_all['criteria_evaluation']['primary_association_supported']},
  rho {solar_all['association_primary_signed_spread']['spearman_rho']:+.4f})
- Both horizons positive (daytime): **{solar_bp['conclusion'].upper()}**
  (gradient {solar_bp['criteria_evaluation']['gradient_directionally_consistent']},
  association {solar_bp['criteria_evaluation']['primary_association_supported']},
  rho {solar_bp['association_primary_signed_spread']['spearman_rho']:+.4f})

## Chart

`p4_3_revision_label_chart_{RUN_DATE}.png` — DOWN / UP / NEUTRAL share by
wind_revision quintile.

## Limitations

- In-sample / descriptive on the full development period; the frozen delta was
  estimated on the same period (E002). A chronological out-of-sample check and
  regime / cross-border conditioning are P4.4 and later.
- Persistence is an ex-post reference (D023 / E001), not a decision-time method.
- Balancing pressure is an ex-post proxy, not executable trading P&L (D016).
"""
    (evidence_dir / f"p4_3_result_{RUN_DATE}.md").write_text(text, encoding="utf-8")


def run(repo_root: Path) -> dict[str, Any]:
    config, frame, bucket_freeze = load_inputs(repo_root)
    evidence_dir = repo_root / "research/evidence/p4_h2_revision"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    c = float(bucket_freeze["wind_revision"]["rule_threshold_c"]["value_mwh"])

    primary = evaluate_variable(
        frame,
        "wind_revision_mwh",
        "wind_revision_available",
        "wind_revision_quintile",
        "wind_revision_decile",
        c,
        "wind_revision_mwh",
        solar_only_label=False,
    )

    solar_c = float(
        frame.loc[frame["solar_revision_available"].fillna(False), "solar_revision_mwh"]
        .abs()
        .quantile(0.60, interpolation="linear")
    )
    solar_all = evaluate_variable(
        frame,
        "solar_revision_mwh",
        "solar_revision_available",
        "solar_revision_quintile",
        "solar_revision_decile",
        solar_c,
        "solar_revision_mwh",
        solar_only_label=True,
    )

    bp_frame = frame.copy()
    bp_frame["solar_bp_available"] = bp_frame["solar_both_horizons_positive"].fillna(False)
    solar_bp_c = float(
        bp_frame.loc[bp_frame["solar_bp_available"], "solar_revision_mwh"]
        .abs()
        .quantile(0.60, interpolation="linear")
    )
    solar_bp = evaluate_variable(
        bp_frame,
        "solar_revision_mwh",
        "solar_bp_available",
        "solar_revision_bothpos_quintile",
        "solar_revision_bothpos_decile",
        solar_bp_c,
        "solar_revision_mwh_both_positive",
        solar_only_label=True,
    )

    chart_path = evidence_dir / f"p4_3_revision_label_chart_{RUN_DATE}.png"
    make_chart(frame, chart_path)

    json_dump(evidence_dir / f"p4_3_wind_primary_{RUN_DATE}.json", primary)
    json_dump(
        evidence_dir / f"p4_3_solar_secondary_{RUN_DATE}.json",
        {"all_numeric_pairs": solar_all, "both_horizons_positive": solar_bp},
    )
    quality = validate_and_report(
        repo_root, config, frame, bucket_freeze, primary, chart_path, evidence_dir
    )
    write_markdown(evidence_dir, primary, solar_all, solar_bp)
    return {"quality": quality, "primary": primary, "solar_all": solar_all, "solar_bp": solar_bp}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = run(args.repo_root.resolve())
    p = report["primary"]
    a = p["association_primary_signed_spread"]
    r = p["transparent_rule"]["scores"]
    print(
        json.dumps(
            {
                "status": report["quality"]["status"],
                "primary_conclusion": p["conclusion"],
                "gradient_spearman": p["contingency_quintile"]["gradient_bucket_index_spearman"],
                "assoc_rho": a["spearman_rho"],
                "assoc_ci": [a["ci_low"], a["ci_high"]],
                "rule_balanced_acc": r["balanced_accuracy"],
                "rule_macro_f1": r["macro_f1"],
                "rule_beats_availability_safe": p["criteria_evaluation"][
                    "rule_beats_availability_safe_baselines"
                ],
                "solar_all_conclusion": report["solar_all"]["conclusion"],
                "solar_bothpos_conclusion": report["solar_bp"]["conclusion"],
                "holdout": report["quality"]["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
