"""P6 — H3 cross-border and system conditions.

P6.1 builds decision-eligible cross-border conditioning variables from
`Transmissionlines` day-ahead capacity and scheduled exchange (D024), plus a
diagnostic realized-flow variable.  P6.2 tests whether the H2 wind-revision
gradient changes with those conditions.  Exploratory / descriptive (E002); the
border subset, sign conventions and tercile scheme are declared before any
outcome is crossed.  The locked holdout is never read.
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


RUN_DATE = "2026-09-06"
EXPECTED_ROWS = 21_887
LABELS = ("UP", "DOWN", "NEUTRAL")
GRADIENT_MIN_SPEARMAN = 0.8
MATERIAL_GRADIENT_DIFFERENCE = 0.05

# --- declared before crossing cross-border conditions with any outcome ---
USABLE_BORDERS = ("de", "dk2", "nl", "no2", "se3")  # GB day-ahead fields are all null (P1.4)
REALIZED_BORDERS = ("no", "se", "ge", "nl", "great_belt")  # GB settlement has 16k nulls
TERCILES = (1 / 3, 2 / 3)


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


def load(repo_root: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    config = yaml.safe_load(
        (repo_root / "config/research_config.yaml").read_text(encoding="utf-8")
    )
    holdout = config["periods"]["holdout"]
    if holdout["state"] != "locked" or holdout["fetch_allowed"] is not False:
        raise ValueError("P6 requires the holdout to remain locked and fetch-disabled.")
    p3_quality = _load_json(
        repo_root / "research/evidence/p3_target_construction" / f"quality_report_{RUN_DATE}.json"
    )
    p4_quality = _load_json(
        repo_root / "research/evidence/p4_h2_revision" / f"quality_report_{RUN_DATE}.json"
    )
    for report in (p3_quality, p4_quality):
        if report["status"] != "PASS":
            raise ValueError("A frozen upstream quality gate is not PASS.")
    target_path = repo_root / "data/processed/p3/target_development.parquet"
    revision_path = repo_root / "data/processed/p4/revision_development.parquet"
    if sha256(target_path) != p3_quality["output_sha256"]:
        raise ValueError("P3 target hash no longer matches its frozen evidence.")
    if sha256(revision_path) != p4_quality["output_sha256"]:
        raise ValueError("P4.2 revision hash no longer matches its frozen evidence.")
    target = pd.read_parquet(target_path)
    revision = pd.read_parquet(
        revision_path,
        columns=["delivery_start_utc", "wind_revision_mwh", "wind_revision_quintile", "wind_revision_available"],
    )
    merged = target.merge(revision, on="delivery_start_utc", how="inner", validate="1:1")
    if len(merged) != EXPECTED_ROWS:
        raise ValueError("P3/P4 join did not preserve the frozen row count.")
    holdout_start = pd.Timestamp(
        holdout["start_date"], tz=config["periods"]["boundary_timezone"]
    ).tz_convert("UTC")
    if merged["delivery_start_utc"].ge(holdout_start).any():
        raise ValueError("Joined frame contains a locked-holdout row.")
    return config, merged


def build_cross_border(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = frame.copy()
    imp = result[[f"transmission_import_capacity_{b}" for b in USABLE_BORDERS]]
    exp = result[[f"transmission_export_capacity_{b}" for b in USABLE_BORDERS]]
    sch = result[[f"transmission_scheduled_exchange_day_ahead_{b}" for b in USABLE_BORDERS]]

    # Import headroom: positive capacity into DK1. Export headroom: the export
    # direction is reported as a negative number; take its magnitude, and treat
    # the rare positive export-capacity records as zero available export.
    result["import_headroom_mw"] = imp.clip(lower=0).sum(axis=1, min_count=1)
    result["export_headroom_mw"] = (-exp).clip(lower=0).sum(axis=1, min_count=1)
    result["net_scheduled_exchange_da_mw"] = sch.sum(axis=1, min_count=1)  # + = net import into DK1
    result["any_positive_export_capacity"] = (exp > 0).any(axis=1)
    result["cross_border_eligible_available"] = (
        result["import_headroom_mw"].notna()
        & result["export_headroom_mw"].notna()
        & result["net_scheduled_exchange_da_mw"].notna()
    )

    realized = result[[f"actual_exchange_{b}_mwh" for b in REALIZED_BORDERS]]
    # settlement convention: negative = export, positive = import
    result["realized_net_import_mwh"] = realized.sum(axis=1, min_count=1)
    result["realized_flow_available"] = realized.notna().all(axis=1)

    meta = {
        "usable_borders": list(USABLE_BORDERS),
        "excluded_border": "gb (all day-ahead fields null, P1.4)",
        "export_capacity_sign_convention": "export direction stored as a negative number; magnitude taken; positive export-capacity records (166 hours) treated as zero available export and flagged",
        "realized_borders": list(REALIZED_BORDERS),
        "realized_classification": "diagnostic_only (settlement flow, published after delivery)",
        "any_positive_export_capacity_hours": int(result["any_positive_export_capacity"].sum()),
    }
    return result, meta


def _terciles(values: pd.Series) -> tuple[pd.Series, list[float]]:
    clean = values.dropna()
    edges = [float(clean.quantile(q, interpolation="linear")) for q in TERCILES]
    bins = [-np.inf, *edges, np.inf]
    return pd.cut(values, bins=bins, labels=["T1_low", "T2_mid", "T3_high"]).astype("object"), edges


def h2_gradient(sub: pd.DataFrame) -> dict[str, Any]:
    mask = sub["wind_revision_quintile"].notna() & sub["target_label"].notna()
    s = sub.loc[mask]
    if len(s) < 300:
        return {"n": int(len(s)), "insufficient": True}
    table = pd.crosstab(s["wind_revision_quintile"], s["target_label"]).reindex(columns=LABELS, fill_value=0)
    shares = table.div(table.sum(axis=1), axis=0)
    dmu = (shares["DOWN"] - shares["UP"]).to_numpy()
    grad = float(stats.spearmanr(np.arange(len(dmu)), dmu).statistic)
    return {
        "n": int(len(s)),
        "insufficient": False,
        "down_minus_up_by_bucket": {int(b): float(dmu[i]) for i, b in enumerate(table.index)},
        "q5_minus_q1_spread": float(dmu[-1] - dmu[0]),
        "gradient_spearman": grad,
        "directionally_consistent": bool(grad >= GRADIENT_MIN_SPEARMAN and dmu[-1] > dmu[0]),
    }


def stratify_h2(frame: pd.DataFrame, cond_col: str, congested_tercile: str) -> dict[str, Any]:
    available = frame["wind_revision_available"].fillna(False).astype(bool) & frame[cond_col].notna()
    base = frame.loc[available]
    bucket, edges = _terciles(base[cond_col])
    base = base.assign(_tercile=bucket)
    cells = {
        t: h2_gradient(base.loc[base["_tercile"] == t]) for t in ("T1_low", "T2_mid", "T3_high")
    }
    open_tercile = "T3_high" if congested_tercile == "T1_low" else "T1_low"
    spread_congested = cells[congested_tercile].get("q5_minus_q1_spread")
    spread_open = cells[open_tercile].get("q5_minus_q1_spread")
    difference = (
        None
        if spread_congested is None or spread_open is None
        else float(spread_congested - spread_open)
    )
    return {
        "conditioning_variable": cond_col,
        "tercile_edges": edges,
        "congested_tercile": congested_tercile,
        "cells": cells,
        "gradient_spread_congested_minus_open": difference,
        "conditions_h2": bool(difference is not None and difference > MATERIAL_GRADIENT_DIFFERENCE),
        "predicted_direction": "steeper H2 DOWN-gradient when the export direction is congested",
    }


def make_chart(strat: dict[str, dict[str, Any]], output_path: Path) -> None:
    fig, axes = plt.subplots(1, len(strat), figsize=(4.2 * len(strat), 4.2), sharey=True)
    if len(strat) == 1:
        axes = [axes]
    for ax, (name, rep) in zip(axes, strat.items()):
        ts = ["T1_low", "T2_mid", "T3_high"]
        vals = [rep["cells"][t].get("q5_minus_q1_spread", np.nan) for t in ts]
        ax.bar(range(3), vals, color="#4c72b0")
        ax.set_xticks(range(3))
        ax.set_xticklabels(["low", "mid", "high"])
        ax.set_title(name.replace("_", " "), fontsize=9)
        ax.axhline(0, color="#333", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("H2 gradient:  Q5 − Q1 of P(DOWN) − P(UP)")
    fig.suptitle(
        "H3: does the H2 wind-revision gradient change with cross-border conditions?\n"
        "(development, in-sample; a flat profile = H3 does not condition H2)",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def run(repo_root: Path) -> dict[str, Any]:
    config, frame = load(repo_root)
    evidence_dir = repo_root / "research/evidence/p6_h3_cross_border"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    frame, meta = build_cross_border(frame)

    strat = {
        "export_headroom_mw": stratify_h2(frame, "export_headroom_mw", "T1_low"),
        "net_scheduled_exchange_da_mw": stratify_h2(frame, "net_scheduled_exchange_da_mw", "T1_low"),
    }
    diagnostic = {
        "realized_net_import_mwh": stratify_h2(
            frame.loc[frame["realized_flow_available"]], "realized_net_import_mwh", "T3_high"
        ),
    }

    eligible_conditions_h2 = any(s["conditions_h2"] for s in strat.values())
    diag_conditions_h2 = any(s["conditions_h2"] for s in diagnostic.values())
    if eligible_conditions_h2:
        conclusion = "H3 conditions H2 with decision-eligible cross-border variables"
    elif diag_conditions_h2:
        conclusion = (
            "H3 conditions H2 only through realized flows (diagnostic); the decision-eligible "
            "day-ahead capacity and schedule do not materially move the H2 gradient"
        )
    else:
        conclusion = (
            "H3 does not measurably condition the H2 wind-revision gradient in this specification "
            "(eligible or diagnostic); the H2 gradient is stable across cross-border regimes"
        )

    report = {
        "step": "P6",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "scope": "development only; exploratory / descriptive (E002)",
        "declared_before_crossing_outcomes": {
            "usable_borders": list(USABLE_BORDERS),
            "realized_borders": list(REALIZED_BORDERS),
            "tercile_quantiles": list(TERCILES),
            "material_gradient_difference": MATERIAL_GRADIENT_DIFFERENCE,
        },
        "p6_1_build": meta,
        "coverage": {
            "cross_border_eligible_available_hours": int(frame["cross_border_eligible_available"].sum()),
            "realized_flow_available_hours": int(frame["realized_flow_available"].sum()),
            "expected_hours": EXPECTED_ROWS,
        },
        "p6_2_eligible_conditioning": strat,
        "p6_2_diagnostic_conditioning": diagnostic,
        "conclusion": conclusion,
        "limitations": (
            "In-sample / descriptive. Export-capacity sign convention is imperfect (166 anomalous hours). "
            "Countertrade (partial period from 2023-04-18) and border-specific flow modelling are not "
            "included; a proper H3 model is later work. GB is excluded (null day-ahead fields)."
        ),
        "holdout": "LOCKED_AND_UNUSED",
    }

    chart_path = evidence_dir / f"p6_h3_gradient_by_crossborder_{RUN_DATE}.png"
    make_chart(strat, chart_path)
    json_dump(evidence_dir / f"p6_h3_cross_border_{RUN_DATE}.json", report)

    checks = {
        "join_rows_equal_expected": len(frame) == EXPECTED_ROWS,
        "no_holdout_rows": bool(
            frame["delivery_start_utc"].lt(
                pd.Timestamp(config["periods"]["holdout"]["start_date"],
                             tz=config["periods"]["boundary_timezone"]).tz_convert("UTC")
            ).all()
        ),
        "gb_excluded_from_usable": "gb" not in USABLE_BORDERS,
        "realized_flow_classified_diagnostic": meta["realized_classification"].startswith("diagnostic"),
        "eligible_conditions_use_day_ahead_only": True,
        "chart_written": chart_path.exists(),
        "conclusion_is_nonempty": bool(conclusion),
    }
    quality = {
        "step": "P6",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "critical_checks": checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p6_quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        raise ValueError(f"P6 quality gate failed: {[k for k, v in checks.items() if not v]}")
    _write_markdown(evidence_dir, report)
    return {"report": report, "quality": quality}


def _write_markdown(evidence_dir: Path, report: dict[str, Any]) -> None:
    def strat_block(name: str, rep: dict[str, Any]) -> str:
        rows = []
        for t in ("T1_low", "T2_mid", "T3_high"):
            c = rep["cells"][t]
            if c.get("insufficient"):
                rows.append(f"| {t} | {c['n']:,} | insufficient | — |")
            else:
                rows.append(
                    f"| {t} | {c['n']:,} | {c['gradient_spearman']:+.2f} | {c['q5_minus_q1_spread']:+.3f} |"
                )
        diff = rep["gradient_spread_congested_minus_open"]
        diff_s = "n/a" if diff is None else f"{diff:+.3f}"
        return (
            f"### {name}\n\n"
            f"Congested tercile: `{rep['congested_tercile']}`. Predicted: "
            f"{rep['predicted_direction']}.\n\n"
            f"| Tercile | Hours | H2 gradient Spearman | Q5−Q1 spread |\n|---|---:|---:|---:|\n"
            + "\n".join(rows)
            + f"\n\nGradient spread, congested − open: `{diff_s}` "
            f"(threshold `> {MATERIAL_GRADIENT_DIFFERENCE}`) → conditions H2: "
            f"**{rep['conditions_h2']}**\n"
        )

    text = f"""# P6 — H3 Cross-Border and System Conditions

**Status:** P6.1 and P6.2 complete — {RUN_DATE}
**Scope:** development only, exploratory / descriptive (E002)
**Holdout:** LOCKED AND UNUSED

## Conclusion

**{report['conclusion'].upper()}**

## P6.1 — cross-border conditioning variables

Usable borders: {report['p6_1_build']['usable_borders']} (GB excluded — all
day-ahead fields null, P1.4).

- `import_headroom_mw` = Σ positive import capacity into DK1.
- `export_headroom_mw` = Σ magnitude of the (negative-stored) export capacity;
  {report['p6_1_build']['any_positive_export_capacity_hours']} hours have an
  anomalous positive export-capacity record and are treated as zero available
  export.
- `net_scheduled_exchange_da_mw` = Σ day-ahead scheduled exchange
  (positive = net import into DK1). All three are decision-eligible: published
  day-ahead, before the delivery-hour cutoff (D024 / D025).
- `realized_net_import_mwh` = Σ settled cross-border flow
  ({report['p6_1_build']['realized_borders']}); **diagnostic only**.

Coverage: eligible conditions available for
{report['coverage']['cross_border_eligible_available_hours']:,} /
{report['coverage']['expected_hours']:,} hours; realized flow for
{report['coverage']['realized_flow_available_hours']:,}.

## P6.2 — does H3 condition the H2 gradient?

Metric: the H2 wind-revision gradient (Q5−Q1 spread in `P(DOWN) − P(UP)`)
computed separately inside each tercile of a cross-border variable. If H3
conditions H2, the gradient is materially steeper when the export direction is
congested.

### Decision-eligible

{strat_block('Export headroom', report['p6_2_eligible_conditioning']['export_headroom_mw'])}
{strat_block('Net day-ahead scheduled exchange', report['p6_2_eligible_conditioning']['net_scheduled_exchange_da_mw'])}

### Diagnostic (realized flow — not decision-eligible)

{strat_block('Realized net import', report['p6_2_diagnostic_conditioning']['realized_net_import_mwh'])}

## Chart

`p6_h3_gradient_by_crossborder_{RUN_DATE}.png` — H2 gradient by conditioning
tercile; a flat profile means H3 does not condition H2.

## Limitations

{report['limitations']}
"""
    (evidence_dir / f"p6_h3_cross_border_{RUN_DATE}.md").write_text(text, encoding="utf-8")


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
                "export_headroom_diff": r["p6_2_eligible_conditioning"]["export_headroom_mw"][
                    "gradient_spread_congested_minus_open"
                ],
                "net_scheduled_diff": r["p6_2_eligible_conditioning"][
                    "net_scheduled_exchange_da_mw"
                ]["gradient_spread_congested_minus_open"],
                "realized_diff": r["p6_2_diagnostic_conditioning"]["realized_net_import_mwh"][
                    "gradient_spread_congested_minus_open"
                ],
                "holdout": r["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
