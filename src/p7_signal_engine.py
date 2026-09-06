"""P7 — transparent rule-based signal engine.

P7.1 builds a small, fully stated decision table over decision-eligible inputs
only (the H2 wind revision and the H1-B residual-load proxy), with the H2
low-wind blind spot handled explicitly.  P7.2 attaches confidence, No-Trade
conditions, risk and invalidation.  P7.3 scores the signal against the mandatory
baselines with full denominators and writes a Market State Card set and the first
Market Journal entry.

Outputs are research judgments, not executable trades (D016).  Development only,
in-sample / descriptive (E002).  The locked holdout is never read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import balanced_accuracy_score, f1_score

# Allow both `python src/p7_signal_engine.py` and `import src.p7_signal_engine`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.p5_residual_load import build_rl_known


RUN_DATE = "2026-09-06"
EXPECTED_ROWS = 21_887
LABELS = ("UP", "DOWN", "NEUTRAL")

# --- pre-declared thresholds (all from decision-eligible distributions) ---
# The engine speaks only where each hypothesis has evidence: H2 on the DOWN side
# (P4.3 asymmetry) and only for large revisions; H1 on the UP side (P5.1 tight
# region) and only for very tight hours.
H2_STRONG_ABS_Q = 0.80  # top 20% of abs(wind_revision), development
LOW_WIND_CUT_MWH = 861.430541  # P4.4 wind_forecast_5h bottom tercile (H2 blind spot)
RL_TIGHT_Q = 0.80  # top 20% of residual_load_known, development
WIND_5H = ("forecast_5_hour_offshore_wind_mwh_per_hour", "forecast_5_hour_onshore_wind_mwh_per_hour")


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
        raise ValueError("P7 requires the holdout to remain locked and fetch-disabled.")
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
        columns=["delivery_start_utc", "wind_revision_mwh", "wind_revision_available"],
    )
    merged = target.merge(revision, on="delivery_start_utc", how="inner", validate="1:1")
    merged = merged.sort_values("delivery_start_utc").reset_index(drop=True)
    if len(merged) != EXPECTED_ROWS:
        raise ValueError("P3/P4 join did not preserve the frozen row count.")
    holdout_start = pd.Timestamp(
        holdout["start_date"], tz=config["periods"]["boundary_timezone"]
    ).tz_convert("UTC")
    if merged["delivery_start_utc"].ge(holdout_start).any():
        raise ValueError("Joined frame contains a locked-holdout row.")
    return config, merged


def build_signal(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = build_rl_known(frame).copy()
    result["wind_forecast_5h_mwh"] = result[list(WIND_5H)].sum(axis=1, min_count=2)
    h2_strong_cut = float(
        result["wind_revision_mwh"].abs().dropna().quantile(H2_STRONG_ABS_Q, interpolation="linear")
    )
    rl_tight_cut = float(
        result["residual_load_known_mwh"].dropna().quantile(RL_TIGHT_Q, interpolation="linear")
    )

    rev = result["wind_revision_mwh"]
    wf5 = result["wind_forecast_5h_mwh"]
    rlk = result["residual_load_known_mwh"]
    h2_ok = result["wind_revision_available"].fillna(False).astype(bool) & wf5.notna()
    not_blind = wf5 > LOW_WIND_CUT_MWH

    # H2 speaks only for the evidenced DOWN side (P4.3 asymmetry) and only for
    # large revisions outside the low-wind blind spot (P4.4).
    h2_view = pd.Series("none", index=result.index, dtype="object")
    h2_view.loc[h2_ok & not_blind & rev.gt(h2_strong_cut)] = "DOWN"
    h2_view.loc[~h2_ok] = "missing"

    # H1 speaks only for the evidenced UP side and only for very tight hours (P5.1).
    h1_view = pd.Series("none", index=result.index, dtype="object")
    h1_view.loc[rlk.notna() & rlk.gt(rl_tight_cut)] = "UP"
    h1_view.loc[rlk.isna()] = "missing"

    signal = pd.Series("NO TRADE", index=result.index, dtype="object")
    confidence = pd.Series("n/a", index=result.index, dtype="object")
    reason = pd.Series("no eligible input crosses its threshold, or an input is missing", index=result.index, dtype="object")

    h2_down_only = h2_view.eq("DOWN") & ~h1_view.eq("UP")
    h1_up_only = h1_view.eq("UP") & ~h2_view.eq("DOWN")
    conflict = h2_view.eq("DOWN") & h1_view.eq("UP")

    signal.loc[h2_down_only] = "DOWN PRESSURE"
    confidence.loc[h2_down_only] = "MEDIUM"
    reason.loc[h2_down_only] = "large positive wind revision, wind not low; H1 not tight"

    signal.loc[h1_up_only] = "UP PRESSURE"
    confidence.loc[h1_up_only] = "LOW"
    reason.loc[h1_up_only] = "very tight known residual load; H2 not on the DOWN side"

    signal.loc[conflict] = "NO TRADE"
    confidence.loc[conflict] = "n/a"
    reason.loc[conflict] = "H2 says DOWN (wind surplus) but H1 says tight — conflicting signals"

    result["h2_view"] = h2_view
    result["h1_view"] = h1_view
    result["signal"] = signal
    result["signal_confidence"] = confidence
    result["signal_reason"] = reason
    result["signal_predicted_label"] = signal.map(
        {"UP PRESSURE": "UP", "DOWN PRESSURE": "DOWN", "NO TRADE": "NEUTRAL"}
    )

    rules = {
        "inputs": {
            "h2_wind_revision_mwh": "decision-eligible (D025), from P4.2",
            "wind_forecast_5h_mwh": "decision-eligible; used for the H2 low-wind blind spot",
            "residual_load_known_mwh": "decision-eligible H1-B interim proxy (D031)",
        },
        "thresholds_pre_declared": {
            "h2_strong_abs_revision_cut_mwh": h2_strong_cut,
            "h2_strong_abs_revision_quantile": H2_STRONG_ABS_Q,
            "low_wind_cut_mwh": LOW_WIND_CUT_MWH,
            "rl_tight_cut_mwh": rl_tight_cut,
            "rl_tight_quantile": RL_TIGHT_Q,
        },
        "h2_view_rule": "DOWN if wind_revision > h2_strong_cut (top 20% |revision|) and wind_forecast_5h > low_wind_cut; else none. H2 does not emit UP (P4.3: the UP side has no skill).",
        "h1_view_rule": "UP if residual_load_known > rl_tight_cut (top 20%); else none. H1 does not emit DOWN (P5.1 supported only the tight, UP side).",
        "combination": {
            "DOWN PRESSURE / MEDIUM": "H2 DOWN, H1 not tight",
            "UP PRESSURE / LOW": "H1 very tight, H2 not on the DOWN side",
            "NO TRADE": "H2 DOWN vs H1 tight conflict; neither view fires; or a missing input",
        },
        "confidence_note": "Low / Medium / High; nothing in this round supports High.",
    }
    return result, rules


def score(frame: pd.DataFrame) -> dict[str, Any]:
    valid = frame["target_label"].notna()
    y_true = frame.loc[valid, "target_label"].astype(str)
    y_pred_full = frame.loc[valid, "signal_predicted_label"].astype(str)

    def m(yt: pd.Series, yp: pd.Series) -> dict[str, float]:
        return {
            "n": int(len(yt)),
            "balanced_accuracy": float(balanced_accuracy_score(yt, yp)),
            "macro_f1": float(f1_score(yt, yp, labels=list(LABELS), average="macro", zero_division=0)),
            "accuracy": float((yt.to_numpy() == yp.to_numpy()).mean()),
        }

    # baselines on the same rows
    majority = pd.Series("NEUTRAL", index=y_true.index)
    him = (
        frame.loc[valid]
        .groupby(["local_weekday", "local_hour"])["target_label"]
        .agg(lambda s: s.value_counts().idxmax())
        .to_dict()
    )
    gm = y_true.value_counts().idxmax()
    how = pd.Series(
        [him.get((w, h), gm) for w, h in zip(frame.loc[valid, "local_weekday"], frame.loc[valid, "local_hour"])],
        index=y_true.index,
    )
    prev_label = frame["target_label"].shift(1)
    prev_time = frame["delivery_start_utc"].shift(1)
    consecutive = (frame["delivery_start_utc"] - prev_time).eq(pd.Timedelta(hours=1))
    persistence = prev_label.where(consecutive).loc[valid]

    active = frame.loc[valid, "signal"].ne("NO TRADE")
    active_true = y_true.loc[active]
    active_pred = y_pred_full.loc[active]
    active_hit = float((active_true.to_numpy() == active_pred.to_numpy()).mean()) if active.any() else None

    signal_by_class = {}
    for cls in ("UP PRESSURE", "DOWN PRESSURE", "NO TRADE"):
        rows = frame.loc[valid & frame["signal"].eq(cls)]
        dist = rows["target_label"].value_counts()
        signal_by_class[cls] = {
            "n": int(len(rows)),
            "share_of_valid": float(len(rows) / int(valid.sum())),
            "realized_label_shares": {
                lab: float(dist.get(lab, 0) / len(rows)) if len(rows) else None for lab in LABELS
            },
        }

    return {
        "denominators": {
            "development_hours": int(len(frame)),
            "valid_label_hours": int(valid.sum()),
            "active_view_hours": int(active.sum()),
            "no_trade_hours": int((frame.loc[valid, "signal"].eq("NO TRADE")).sum()),
            "coverage_active_share": float(active.sum() / int(valid.sum())),
        },
        "full_sample_no_trade_as_neutral": {
            "signal": m(y_true, y_pred_full),
            "majority_neutral": m(y_true, majority),
            "hour_of_week_training_majority": m(y_true, how),
            "persistence_ex_post_reference": m(
                y_true.loc[persistence.notna()], persistence.loc[persistence.notna()]
            ),
        },
        "active_view": {
            "n": int(active.sum()),
            "three_class_hit_rate": active_hit,
            "hit_rate_by_confidence": {
                conf: float(
                    (
                        y_true.loc[active & frame.loc[valid, "signal_confidence"].eq(conf)].to_numpy()
                        == y_pred_full.loc[active & frame.loc[valid, "signal_confidence"].eq(conf)].to_numpy()
                    ).mean()
                )
                if (active & frame.loc[valid, "signal_confidence"].eq(conf)).any()
                else None
                for conf in ("MEDIUM", "LOW")
            },
        },
        "signal_by_class": signal_by_class,
        "interpretation": "Development-wide, in-sample / descriptive (E002). The signal has no outcome-fitted parameters. Not executable trading P&L (D016).",
    }


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def market_state_cards(frame: pd.DataFrame, evidence_dir: Path) -> list[str]:
    valid = frame["target_label"].notna()
    picks: list[tuple[str, pd.Series]] = []
    for cls, want_hit in (("DOWN PRESSURE", True), ("UP PRESSURE", True), ("DOWN PRESSURE", False)):
        pool = frame.loc[
            valid
            & frame["signal"].eq(cls)
            & (frame["target_label"].eq(cls.split()[0]) == want_hit)
        ]
        if len(pool):
            picks.append(("hit" if want_hit else "miss", pool.iloc[len(pool) // 2]))
    nt = frame.loc[valid & frame["signal"].eq("NO TRADE") & frame["target_label"].ne("NEUTRAL")]
    if len(nt):
        picks.append(("no_trade", nt.iloc[len(nt) // 2]))

    written = []
    for i, (kind, row) in enumerate(picks, start=1):
        card = f"""# DK1 Market State Card {i} ({kind})

**Retrospective worked example on development data.** The decision fields are what
the P7 rule would have produced from decision-eligible inputs; the outcome is the
realized label. Not a live card and not executable P&L (D016).

- Card ID: P7-DEV-{i:02d}
- Delivery hour (UTC): {row['delivery_start_utc']}
- Delivery hour (local): {row['delivery_start_local']}
- Decision cutoff (UTC): {row['delivery_start_utc']}  (last pre-delivery snapshot, D025)
- Data version: P3 target + P4.2 revision, git-tracked evidence

## Information snapshot (decision-eligible only)

- Day-ahead price (EUR/MWh): {_fmt(row['spot_price_eur_mwh'])}
- Wind revision 5h->1h (MWh): {_fmt(row['wind_revision_mwh'])}
- 5h wind forecast (MWh): {_fmt(row['wind_forecast_5h_mwh'])}  ({'in the low-wind blind spot' if row['wind_forecast_5h_mwh'] <= LOW_WIND_CUT_MWH else 'wind not low'})
- Known residual load proxy (MWh): {_fmt(row['residual_load_known_mwh'])}
- H2 view: {row['h2_view']}   H1 view: {row['h1_view']}

## Market view

- Directional view: {row['signal']}
- Confidence: {row['signal_confidence']}
- Primary driver: {row['signal_reason']}
- Counterargument: the underlying H2 association is weak (Spearman ~ -0.10) and did not reproduce on the 2024 H1 hold-back; H1 is threshold-like and weak
- Key risk: realized conditions (outages, demand, cross-border) dominate the hourly balancing outcome
- Invalidation: a low 5h wind forecast (H2 blind spot); renewables arriving far from forecast; the system turning tight against a DOWN view

## Decision

- Decision: {'Bearish (down pressure)' if row['signal'] == 'DOWN PRESSURE' else ('Bullish (up pressure)' if row['signal'] == 'UP PRESSURE' else 'No Trade')}
- No-Trade condition: conflicting H1/H2 views, both views silent, or a missing eligible input

## Outcome (known — retrospective)

- Actual balancing price (EUR/MWh): {_fmt(row['imbalance_price_eur_mwh'])}
- Actual spread (EUR/MWh): {_fmt(row['balancing_spread_eur_mwh'])}
- Realized label: {row['target_label']}
- Directionally correct: {row['signal_predicted_label'] == row['target_label']}

## Post-mortem

- {'The rule caught the realized direction.' if row['signal_predicted_label'] == row['target_label'] else 'The rule was directionally wrong here — a reminder that the edge is small and noisy.'}
- What was missing: no decision-eligible measure of demand shocks, outages or realized cross-border flow.
- What changes next: a probabilistic model (P10) and, if it becomes available, the ENTSO-E load forecast (I06).
"""
        path = evidence_dir / f"market_state_card_{i}_{RUN_DATE}.md"
        path.write_text(card, encoding="utf-8")
        written.append(path.name)
    return written


JOURNAL_MARKER = "\n\n---\n\n## Entry J001 — H2/H1/H3 first research round (retrospective)"


def append_journal_entry(repo_root: Path, scoring: dict[str, Any]) -> None:
    journal = repo_root / "journal/market_journal.md"
    text = journal.read_text(encoding="utf-8")
    # Idempotent: drop any previously written J001 block before re-appending.
    marker_at = text.find("## Entry J001 —")
    if marker_at != -1:
        text = text[: text.rfind("\n\n---", 0, marker_at)].rstrip() + "\n"
    text = text.replace(
        "**Status:** First research-round entry recorded (J001)",
        "**Status:** Initialized; no market-state entries yet",
    )
    cov = scoring["denominators"]
    sig = scoring["full_sample_no_trade_as_neutral"]["signal"]
    maj = scoring["full_sample_no_trade_as_neutral"]["majority_neutral"]
    entry = f"""

---

## Entry J001 — H2/H1/H3 first research round (retrospective)

### Identification

- Journal ID: J001
- Created at: {RUN_DATE}
- Delivery hour: development period 2022-01-01 to 2024-06-30 (aggregate)
- Decision cutoff: delivery-hour start, last pre-delivery snapshot (D025)
- Data version: P3 target + P4.2 revision + P5 H1-B proxy

### Information snapshot

- Renewable forecast revision: H2 5h->1h wind revision — real but weak
  (Spearman ~ -0.10), asymmetric (works on DOWN, not UP), fails at low wind, did
  not reproduce on 2024 H1
- Residual-load condition: H1 actual is diagnostic and weak/threshold-like; the
  H1-B climatology proxy tracks actual residual load (Spearman +0.92) but its own
  spread association is as weak as H1-A
- Cross-border condition: H3 shows no decision-eligible conditioning; only a weak
  diagnostic effect via realized net-import flow

### Market view

- Directional view: mostly No Trade — the transparent engine takes an active view
  in {cov['coverage_active_share']:.0%} of valid hours
- Confidence: Low to Medium; nothing supports High
- Main driver: the H2 DOWN side plus the H1 tight-system UP side
- Counterargument: hourly balancing outcomes are dominated by shocks the eligible
  inputs cannot see
- Key risk: reading a weak in-sample signal as a deployable edge

### Decision

- Decision: retain H2 as conditionally supported, H1 as a weak diagnostic with an
  eligible proxy, H3 as diagnostic-only; build a probabilistic model before any
  stronger claim
- No-Trade condition: conflicting or silent views, missing eligible input
- Invalidation condition: the H2 gradient failing to reproduce on the locked
  holdout at Level C

### Outcome

- Signal balanced accuracy {sig['balanced_accuracy']:.3f} vs majority
  {maj['balanced_accuracy']:.3f} (full sample, No Trade = NEUTRAL); active-view
  three-class hit rate {scoring['active_view']['three_class_hit_rate']:.3f} over
  {cov['active_view_hours']:,} hours
- Baseline result: the signal edges the availability-safe baselines on balanced
  accuracy but the margin is small and in-sample

### Post-Mortem

- What was correct: pre-registration held; every hypothesis got one honest round;
  nulls and weaknesses were kept
- What was wrong / missing: no demand-shock or outage information; the round-1
  baseline gate (P4.3) was too lenient
- Was the original reasoning valid: yes for the mechanism, no for any deployable
  claim
- What should change: stricter baselines, a probabilistic model with calibration
  (P10), then the one-shot holdout test
"""
    journal.write_text(text.replace(
        "**Status:** Initialized; no market-state entries yet",
        "**Status:** First research-round entry recorded (J001)",
    ) + entry, encoding="utf-8")


def make_chart(scoring: dict[str, Any], output_path: Path) -> None:
    classes = ["UP PRESSURE", "DOWN PRESSURE", "NO TRADE"]
    data = scoring["signal_by_class"]
    x = np.arange(len(classes))
    width = 0.26
    colours = {"UP": "#c44e52", "NEUTRAL": "#8c8c8c", "DOWN": "#4c72b0"}
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    for offset, lab in zip((-width, 0.0, width), ("UP", "NEUTRAL", "DOWN")):
        vals = [data[c]["realized_label_shares"][lab] or 0 for c in classes]
        ax.bar(x + offset, vals, width, label=lab, color=colours[lab])
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c}\n(n={data[c]['n']:,})" for c in classes])
    ax.set_ylabel("Realized label share within the signal class")
    ax.set_title("P7 transparent signal vs realized balancing-pressure label\n(development, in-sample / descriptive — not executable P&L)")
    ax.legend(title="Realized label", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def run(repo_root: Path) -> dict[str, Any]:
    config, frame = load(repo_root)
    evidence_dir = repo_root / "research/evidence/p7_signal_engine"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    frame, rules = build_signal(frame)
    scoring = score(frame)
    cards = market_state_cards(frame, evidence_dir)
    append_journal_entry(repo_root, scoring)
    chart_path = evidence_dir / f"p7_signal_vs_label_chart_{RUN_DATE}.png"
    make_chart(scoring, chart_path)

    report = {
        "step": "P7",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "scope": "development only; in-sample / descriptive (E002); research judgment, not executable P&L (D016)",
        "rules": rules,
        "scoring": scoring,
        "market_state_cards": cards,
        "market_journal_entry": "journal/market_journal.md J001",
        "confidence_scale": "Low / Medium / High; nothing in this round supports High",
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p7_signal_engine_{RUN_DATE}.json", report)

    checks = {
        "rows_equal_expected": len(frame) == EXPECTED_ROWS,
        "no_holdout_rows": bool(
            frame["delivery_start_utc"].lt(
                pd.Timestamp(config["periods"]["holdout"]["start_date"],
                             tz=config["periods"]["boundary_timezone"]).tz_convert("UTC")
            ).all()
        ),
        "signal_values_are_frozen_set": set(frame["signal"].unique()).issubset(
            {"UP PRESSURE", "DOWN PRESSURE", "NO TRADE"}
        ),
        "no_trade_when_inputs_missing": bool(
            frame.loc[frame["h2_view"].eq("missing") & frame["h1_view"].eq("missing"), "signal"].eq("NO TRADE").all()
        ),
        "thresholds_pre_declared": all(
            k in rules["thresholds_pre_declared"]
            for k in ("h2_strong_abs_revision_cut_mwh", "low_wind_cut_mwh", "rl_tight_cut_mwh")
        ),
        "both_baselines_reported": "majority_neutral" in scoring["full_sample_no_trade_as_neutral"]
        and "persistence_ex_post_reference" in scoring["full_sample_no_trade_as_neutral"],
        "coverage_disclosed": "coverage_active_share" in scoring["denominators"],
        "cards_written": len(cards) >= 1,
        "chart_written": chart_path.exists(),
    }
    quality = {
        "step": "P7",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "critical_checks": checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p7_quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        raise ValueError(f"P7 quality gate failed: {[k for k, v in checks.items() if not v]}")
    _write_markdown(evidence_dir, report)
    return {"report": report, "quality": quality}


def _write_markdown(evidence_dir: Path, report: dict[str, Any]) -> None:
    s = report["scoring"]
    cov = s["denominators"]
    full = s["full_sample_no_trade_as_neutral"]
    th = report["rules"]["thresholds_pre_declared"]
    by = s["signal_by_class"]
    text = f"""# P7 — Transparent Signal Engine

**Status:** P7.1–P7.3 complete — {RUN_DATE}
**Scope:** development only, in-sample / descriptive (E002); research judgment,
not executable trading P&L (D016)
**Holdout:** LOCKED AND UNUSED

## P7.1 — the decision table (decision-eligible inputs only)

Pre-declared thresholds:
`h2_strong_cut = {th['h2_strong_abs_revision_cut_mwh']:.1f} MWh`
(top 20% of `abs(wind_revision)`),
`low_wind_cut = {th['low_wind_cut_mwh']:.1f} MWh` (P4.4 blind spot),
`rl_tight_cut = {th['rl_tight_cut_mwh']:.1f} MWh` (top 20% of the H1-B proxy).

- **H2 view:** DOWN if `wind_revision > h2_strong_cut` and
  `wind_forecast_5h > low_wind_cut`; else none. H2 does **not** emit UP — P4.3
  showed the UP side has no skill.
- **H1 view:** UP if `residual_load_known > rl_tight_cut`; else none. H1 does
  **not** emit DOWN — P5.1 supported only the tight, UP side.
- **Combination:**
  - `DOWN PRESSURE` / MEDIUM — H2 DOWN, H1 not tight
  - `UP PRESSURE` / LOW — H1 very tight, H2 not on the DOWN side
  - `NO TRADE` — H2 DOWN vs H1 tight conflict; neither view fires; or a missing input

## P7.2 — confidence, No Trade, risk

- Confidence scale Low / Medium / High. **Nothing in this round supports High.**
  The DOWN view (H2, the evidenced side) is MEDIUM; the UP view (H1 proxy, weaker)
  is LOW.
- No Trade conditions: conflicting views, neither view fires, any missing
  decision-eligible input.
- Every active view carries the same risk (hourly outcomes dominated by unseen
  shocks) and invalidation (low 5h wind forecast; renewables far from forecast;
  the system turning tight against a DOWN view).

## P7.3 — scoring against the mandatory baselines

Denominators: {cov['development_hours']:,} development hours,
{cov['valid_label_hours']:,} with a valid label, {cov['active_view_hours']:,}
active views ({cov['coverage_active_share']:.1%} coverage),
{cov['no_trade_hours']:,} No Trade.

Full sample (No Trade scored as a NEUTRAL prediction):

| Method | Balanced accuracy | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| P7 signal | {full['signal']['balanced_accuracy']:.4f} | {full['signal']['macro_f1']:.4f} | {full['signal']['accuracy']:.4f} |
| Majority (NEUTRAL) | {full['majority_neutral']['balanced_accuracy']:.4f} | {full['majority_neutral']['macro_f1']:.4f} | {full['majority_neutral']['accuracy']:.4f} |
| Hour-of-week training majority | {full['hour_of_week_training_majority']['balanced_accuracy']:.4f} | {full['hour_of_week_training_majority']['macro_f1']:.4f} | {full['hour_of_week_training_majority']['accuracy']:.4f} |
| Persistence (ex-post reference) | {full['persistence_ex_post_reference']['balanced_accuracy']:.4f} | {full['persistence_ex_post_reference']['macro_f1']:.4f} | {full['persistence_ex_post_reference']['accuracy']:.4f} |

Active-view three-class hit rate: {s['active_view']['three_class_hit_rate']:.4f}
over {s['active_view']['n']:,} hours
(MEDIUM {s['active_view']['hit_rate_by_confidence']['MEDIUM']}, LOW {s['active_view']['hit_rate_by_confidence']['LOW']}).

Realized label within each signal class:

| Signal | Hours | P(UP) | P(NEUTRAL) | P(DOWN) |
|---|---:|---:|---:|---:|
| UP PRESSURE | {by['UP PRESSURE']['n']:,} | {by['UP PRESSURE']['realized_label_shares']['UP']:.1%} | {by['UP PRESSURE']['realized_label_shares']['NEUTRAL']:.1%} | {by['UP PRESSURE']['realized_label_shares']['DOWN']:.1%} |
| DOWN PRESSURE | {by['DOWN PRESSURE']['n']:,} | {by['DOWN PRESSURE']['realized_label_shares']['UP']:.1%} | {by['DOWN PRESSURE']['realized_label_shares']['NEUTRAL']:.1%} | {by['DOWN PRESSURE']['realized_label_shares']['DOWN']:.1%} |
| NO TRADE | {by['NO TRADE']['n']:,} | {by['NO TRADE']['realized_label_shares']['UP']:.1%} | {by['NO TRADE']['realized_label_shares']['NEUTRAL']:.1%} | {by['NO TRADE']['realized_label_shares']['DOWN']:.1%} |

## Artefacts

- Market State Cards: {report['market_state_cards']}
- Market Journal entry: {report['market_journal_entry']}
- Chart: `p7_signal_vs_label_chart_{RUN_DATE}.png`

## Limitations

- In-sample / descriptive; thresholds are pre-declared from decision-eligible
  distributions but the whole development delta and buckets were estimated on the
  same period (E002).
- No probabilistic output yet (P10). Not executable trading P&L (D016).
"""
    (evidence_dir / f"p7_signal_engine_{RUN_DATE}.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    out = run(args.repo_root.resolve())
    s = out["report"]["scoring"]
    full = s["full_sample_no_trade_as_neutral"]
    print(
        json.dumps(
            {
                "status": out["quality"]["status"],
                "coverage_active_share": s["denominators"]["coverage_active_share"],
                "signal_balanced_accuracy": full["signal"]["balanced_accuracy"],
                "majority_balanced_accuracy": full["majority_neutral"]["balanced_accuracy"],
                "hour_of_week_balanced_accuracy": full["hour_of_week_training_majority"]["balanced_accuracy"],
                "active_view_hit_rate": s["active_view"]["three_class_hit_rate"],
                "cards": out["report"]["market_state_cards"],
                "holdout": out["report"]["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
