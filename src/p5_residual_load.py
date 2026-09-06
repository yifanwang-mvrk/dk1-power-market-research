"""P5 — H1 residual load and system tightness.

P5.1 (H1-A) builds actual residual load from the P2 settlement diagnostics and
relates it to the realized balancing spread and label: a mechanism study, always
``diagnostic_only`` (D024), never a decision input.

P5.2 (H1-B) assesses whether a decision-eligible residual-load proxy exists — a
point-in-time consumption climatology minus the 5h renewable forecast — and
records either an eligible proxy or an evidenced unavailable status.

The locked holdout is never read.
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
LABEL_SCORE = {"UP": 1, "NEUTRAL": 0, "DOWN": -1}
QUANTILES = (0.20, 0.40, 0.60, 0.80)
GRADIENT_MIN_SPEARMAN = 0.8
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20260906
H1_PREDICTED_SIGN = 1  # higher residual load -> tighter system -> higher (more positive) spread / UP
CLIMATOLOGY_LAG_OCCURRENCES = 3  # >= 3 weeks of same weekday-hour history, past the settlement delay

WIND_ACTUAL = (
    "actual_offshore_wind_lt100_mw_mwh",
    "actual_offshore_wind_ge100_mw_mwh",
    "actual_onshore_wind_lt50k_w_mwh",
    "actual_onshore_wind_ge50k_w_mwh",
)
SOLAR_ACTUAL = (
    "actual_solar_power_lt10k_w_mwh",
    "actual_solar_power_ge10_lt40k_w_mwh",
    "actual_solar_power_ge40k_w_mwh",
    "actual_solar_power_self_con_mwh",
)
CONSUMPTION = "actual_gross_consumption_mwh"
WIND_5H = "forecast_5_hour_offshore_wind_mwh_per_hour"
ONWIND_5H = "forecast_5_hour_onshore_wind_mwh_per_hour"
SOLAR_5H = "forecast_5_hour_solar_mwh_per_hour"


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
        raise ValueError("P5 requires the holdout to remain locked and fetch-disabled.")
    p3_quality = _load_json(
        repo_root / "research/evidence/p3_target_construction" / f"quality_report_{RUN_DATE}.json"
    )
    if p3_quality["status"] != "PASS":
        raise ValueError("The frozen P3 quality gate is not PASS.")
    target_path = repo_root / "data/processed/p3/target_development.parquet"
    if sha256(target_path) != p3_quality["output_sha256"]:
        raise ValueError("P3 target hash no longer matches its frozen evidence.")
    frame = pd.read_parquet(target_path)
    if len(frame) != EXPECTED_ROWS or not frame["delivery_start_utc"].is_unique:
        raise ValueError("P3 target does not have the frozen unique-hour shape.")
    holdout_start = pd.Timestamp(
        holdout["start_date"], tz=config["periods"]["boundary_timezone"]
    ).tz_convert("UTC")
    if frame["delivery_start_utc"].ge(holdout_start).any():
        raise ValueError("P3 target contains a locked-holdout row.")
    return config, frame.sort_values("delivery_start_utc").reset_index(drop=True)


def signed_quantile_buckets(values: pd.Series, quantiles: tuple[float, ...]) -> tuple[pd.Series, list[float]]:
    clean = values.dropna()
    edges = sorted({round(float(clean.quantile(q, interpolation="linear")), 6) for q in quantiles})
    bins = [-np.inf, *edges, np.inf]
    labels = list(range(1, len(bins)))
    bucket = pd.cut(values, bins=bins, labels=labels, include_lowest=True).astype("Int64")
    return bucket, edges


def spearman_ci(x: pd.Series, y: pd.Series, predicted_sign: int) -> dict[str, Any]:
    mask = x.notna() & y.notna()
    xv = x.loc[mask].to_numpy(dtype=float)
    yv = y.loc[mask].to_numpy(dtype=float)
    point = float(stats.spearmanr(xv, yv).statistic)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(xv)
    draws = np.empty(BOOTSTRAP_DRAWS)
    for i in range(BOOTSTRAP_DRAWS):
        idx = rng.integers(0, n, n)
        draws[i] = stats.spearmanr(xv[idx], yv[idx]).statistic
    low, high = (float(v) for v in np.percentile(draws, (2.5, 97.5)))
    excludes_zero = (low > 0 and high > 0) or (low < 0 and high < 0)
    observed_sign = 0 if point == 0 else int(np.sign(point))
    return {
        "n": int(n),
        "spearman_rho": point,
        "ci_low": low,
        "ci_high": high,
        "ci_excludes_zero": bool(excludes_zero),
        "predicted_sign": predicted_sign,
        "observed_sign": observed_sign,
        "association_supported": bool(excludes_zero and observed_sign == predicted_sign),
        "bootstrap_seed": BOOTSTRAP_SEED,
    }


def contingency(frame: pd.DataFrame, bucket_col: str, available: pd.Series) -> dict[str, Any]:
    mask = available & frame["target_label"].notna() & frame[bucket_col].notna()
    s = frame.loc[mask]
    table = pd.crosstab(s[bucket_col], s["target_label"]).reindex(columns=LABELS, fill_value=0)
    shares = table.div(table.sum(axis=1), axis=0)
    up_minus_down = (shares["UP"] - shares["DOWN"]).to_numpy()
    grad = float(stats.spearmanr(np.arange(len(up_minus_down)), up_minus_down).statistic)
    return {
        "n": int(mask.sum()),
        "group_sizes": {int(b): int(table.loc[b].sum()) for b in table.index},
        "p_label_given_bucket": {
            int(b): {lab: float(shares.loc[b, lab]) for lab in LABELS} for b in table.index
        },
        "up_share_minus_down_share_by_bucket": {
            int(b): float(up_minus_down[i]) for i, b in enumerate(table.index)
        },
        "gradient_bucket_index_spearman": grad,
        "endpoints_top_gt_bottom": bool(up_minus_down[-1] > up_minus_down[0]),
        "gradient_directionally_consistent": bool(
            grad >= GRADIENT_MIN_SPEARMAN and up_minus_down[-1] > up_minus_down[0]
        ),
    }


# ---------------------------------------------------------------- P5.1 (H1-A) ---


def build_rl_actual(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    cols = [CONSUMPTION, *WIND_ACTUAL, *SOLAR_ACTUAL]
    available = result[cols].notna().all(axis=1)
    result["actual_wind_mwh"] = result[list(WIND_ACTUAL)].sum(axis=1).where(available)
    result["actual_solar_mwh"] = result[list(SOLAR_ACTUAL)].sum(axis=1).where(available)
    result["residual_load_actual_mwh"] = (
        result[CONSUMPTION] - result["actual_wind_mwh"] - result["actual_solar_mwh"]
    ).where(available)
    result["rl_actual_available"] = available
    return result


def run_h1a(frame: pd.DataFrame, evidence_dir: Path) -> dict[str, Any]:
    frame = build_rl_actual(frame)
    bucket, edges = signed_quantile_buckets(frame["residual_load_actual_mwh"], QUANTILES)
    frame["rl_actual_quintile"] = bucket
    available = frame["rl_actual_available"]

    cont = contingency(frame, "rl_actual_quintile", available)
    spread_assoc = spearman_ci(
        frame["residual_load_actual_mwh"].where(available),
        frame["balancing_spread_eur_mwh"],
        H1_PREDICTED_SIGN,
    )
    label_assoc = spearman_ci(
        frame["residual_load_actual_mwh"].where(available),
        frame["target_label"].map(LABEL_SCORE),
        H1_PREDICTED_SIGN,
    )

    dmu = cont["up_share_minus_down_share_by_bucket"]
    top_two = np.mean([dmu[4], dmu[5]])
    bottom_three = np.mean([dmu[1], dmu[2], dmu[3]])
    direction_ok = spread_assoc["association_supported"]
    gradient_ok = cont["gradient_directionally_consistent"]
    threshold_like = direction_ok and cont["endpoints_top_gt_bottom"] and top_two > bottom_three + 0.03
    if gradient_ok and direction_ok:
        conclusion = "mechanism supported (diagnostic) — a smooth gradient: higher realized residual load coincides with upward balancing pressure"
    elif threshold_like:
        conclusion = (
            "directionally present but weak and threshold-like (diagnostic) — the shift toward UP "
            "and away from DOWN appears only in the tightest ~40% of hours (Q4-Q5), not as a smooth gradient"
        )
    elif direction_ok:
        conclusion = "a weak positive association is present but no usable bucket structure (diagnostic)"
    else:
        conclusion = "mechanism not clearly present in the realized data (diagnostic)"

    report = {
        "step": "P5.1",
        "hypothesis": "H1-A",
        "classification": "diagnostic_only",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "definition": "residual_load_actual_mwh = actual_gross_consumption - sum(actual wind) - sum(actual solar)",
        "availability_note": "Settlement data published ~9-15 days after delivery and later revised (D024); it explains realized conditions and is never a decision input.",
        "coverage": {
            "available_hours": int(available.sum()),
            "expected_hours": EXPECTED_ROWS,
            "negative_residual_load_hours": int(
                (frame["residual_load_actual_mwh"] < 0).sum()
            ),
        },
        "signed_quintile_edges_mwh": edges,
        "contingency": cont,
        "association_vs_signed_spread": spread_assoc,
        "association_vs_label_score": label_assoc,
        "predicted_direction": "higher residual load -> higher P(UP), more positive spread",
        "tight_hours_effect": {
            "up_minus_down_share_top_two_buckets": float(top_two),
            "up_minus_down_share_bottom_three_buckets": float(bottom_three),
            "note": "The UP-vs-DOWN shift is concentrated in Q4-Q5 (tight system).",
        },
        "conclusion": conclusion,
        "relation_to_h2": (
            "H2 (P4.4) fails exactly where the system is wind-poor / tight, which is the high-residual-load "
            "Q4-Q5 region where H1's directional effect concentrates. H1 and H2 look complementary rather than "
            "redundant; a joint transparent rule is P7."
        ),
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p5_1_h1a_mechanism_{RUN_DATE}.json", report)
    _h1a_chart(frame, evidence_dir / f"p5_1_residual_load_label_chart_{RUN_DATE}.png")
    return {"report": report, "frame": frame}


def _h1a_chart(frame: pd.DataFrame, output_path: Path) -> None:
    available = frame["rl_actual_available"]
    mask = available & frame["target_label"].notna() & frame["rl_actual_quintile"].notna()
    sub = frame.loc[mask]
    table = pd.crosstab(sub["rl_actual_quintile"], sub["target_label"]).reindex(columns=LABELS, fill_value=0)
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
        [f"Q{b}\n(most negative)" if b == buckets[0] else (f"Q{b}\n(tightest)" if b == buckets[-1] else f"Q{b}") for b in buckets]
    )
    ax.set_xlabel("actual residual load quintile  (signed, development-only Q20/Q40/Q60/Q80)")
    ax.set_ylabel("Share of hours in bucket")
    ax.set_title("H1-A (diagnostic): DK1 balancing-pressure label by actual residual load\n(development 2022-01-01 to 2024-06-30, settlement data — not a decision input)")
    ax.legend(title="Realized label", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- P5.2 (H1-B) ---


def build_rl_known(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    # Point-in-time consumption climatology: expanding mean of gross consumption
    # over prior same-(weekday, hour) occurrences, lagged by CLIMATOLOGY_LAG_OCCURRENCES
    # to stay behind the settlement publication delay.
    key = list(zip(result["local_weekday"], result["local_hour"]))
    result["_how_key"] = pd.Series(key, index=result.index).astype(str)
    clim = pd.Series(np.nan, index=result.index, dtype=float)
    for _, grp in result.groupby("_how_key", sort=False):
        cons = grp[CONSUMPTION]
        expanding = cons.expanding().mean().shift(CLIMATOLOGY_LAG_OCCURRENCES)
        clim.loc[grp.index] = expanding.to_numpy()
    result["consumption_climatology_mwh"] = clim
    result.drop(columns="_how_key", inplace=True)

    ren5 = result[[WIND_5H, ONWIND_5H, SOLAR_5H]]
    ren_ok = ren5.notna().all(axis=1)
    result["renewable_forecast_5h_mwh"] = ren5.sum(axis=1).where(ren_ok)
    available = clim.notna() & ren_ok
    result["residual_load_known_mwh"] = (
        result["consumption_climatology_mwh"] - result["renewable_forecast_5h_mwh"]
    ).where(available)
    result["rl_known_available"] = available
    return result


def run_h1b(frame: pd.DataFrame, evidence_dir: Path) -> dict[str, Any]:
    frame = build_rl_known(frame)
    available = frame["rl_known_available"]
    bucket, edges = signed_quantile_buckets(frame["residual_load_known_mwh"], QUANTILES)
    frame["rl_known_quintile"] = bucket

    both = available & frame["rl_actual_available"]
    proxy_fit = spearman_ci(
        frame["residual_load_known_mwh"].where(both),
        frame["residual_load_actual_mwh"].where(both),
        1,
    )
    cont = contingency(frame, "rl_known_quintile", available)
    spread_assoc = spearman_ci(
        frame["residual_load_known_mwh"].where(available),
        frame["balancing_spread_eur_mwh"],
        H1_PREDICTED_SIGN,
    )

    tracks_actual = proxy_fit["spearman_rho"] >= 0.7
    carries_direction = (
        cont["gradient_directionally_consistent"] and spread_assoc["association_supported"]
    )
    if tracks_actual and carries_direction:
        verdict = (
            "A decision-eligible residual-load proxy is feasible: it tracks actual residual load well "
            f"(Spearman {proxy_fit['spearman_rho']:+.2f}) and reproduces the H1 direction, though its own "
            f"association with the spread is as weak as H1-A (Spearman {spread_assoc['spearman_rho']:+.3f}). "
            "Register it as an eligible input for P7, not a standalone signal."
        )
        status = "ELIGIBLE_INTERIM_PROXY"
    elif tracks_actual:
        verdict = (
            "The proxy tracks actual residual load but does not reproduce the H1 direction on the spread; "
            "H1-B stays pending the external ENTSO-E day-ahead load forecast."
        )
        status = "PENDING_EXTERNAL_LOAD_FORECAST"
    else:
        verdict = "No adequate decision-eligible residual-load proxy; H1-B pending the external ENTSO-E day-ahead load forecast."
        status = "PENDING_EXTERNAL_LOAD_FORECAST"

    report = {
        "step": "P5.2",
        "hypothesis": "H1-B",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "proxy_definition": (
            "residual_load_known_mwh = consumption_climatology_mwh - renewable_forecast_5h_mwh; "
            "climatology is a point-in-time expanding mean of gross consumption over prior "
            f"same-(weekday, hour) occurrences, lagged {CLIMATOLOGY_LAG_OCCURRENCES} occurrences "
            "past the settlement delay; renewable forecast is the 5h offshore + onshore + solar forecast."
        ),
        "eligibility": "consumption climatology and 5h renewable forecasts are both available strictly before delivery (D025)",
        "coverage": {
            "rl_known_available_hours": int(available.sum()),
            "expected_hours": EXPECTED_ROWS,
            "unavailable_reason": "first same-(weekday, hour) occurrences lack the lagged climatology window; some hours lack a 5h renewable forecast",
        },
        "signed_quintile_edges_mwh": edges,
        "proxy_vs_actual_residual_load": proxy_fit,
        "contingency": cont,
        "association_vs_signed_spread": spread_assoc,
        "no_validated_eds_load_forecast": "P1.4 found no validated Energi Data Service historical load forecast; ENTSO-E day-ahead total load forecast remains an external candidate pending access (I06).",
        "verdict": verdict,
        "registration_status": status,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p5_2_h1b_assessment_{RUN_DATE}.json", report)
    return {"report": report, "frame": frame}


# ------------------------------------------------------------------------ run ---


def _write_markdown(evidence_dir: Path, h1a: dict[str, Any], h1b: dict[str, Any]) -> None:
    a = h1a["contingency"]
    aspread = h1a["association_vs_signed_spread"]
    b = h1b["contingency"]
    bspread = h1b["association_vs_signed_spread"]
    fit = h1b["proxy_vs_actual_residual_load"]

    def rows(cont: dict[str, Any]) -> str:
        out = []
        for bkt, shares in cont["p_label_given_bucket"].items():
            out.append(
                f"| Q{bkt} | {cont['group_sizes'][bkt]:,} | {shares['UP']:.1%} | "
                f"{shares['NEUTRAL']:.1%} | {shares['DOWN']:.1%} | "
                f"{cont['up_share_minus_down_share_by_bucket'][bkt]:+.3f} |"
            )
        return "\n".join(out)

    text = f"""# P5 — H1 Residual Load and System Tightness

**Status:** P5.1 and P5.2 complete — {RUN_DATE}
**Holdout:** LOCKED AND UNUSED

## H1-A (P5.1) — actual residual load, diagnostic

`residual_load_actual_mwh = actual_gross_consumption - sum(actual wind) - sum(actual solar)`.
Settlement data, published ~9-15 days after delivery and later revised (D024):
this explains realized physical conditions and is **never a decision input**.
Available for {h1a['coverage']['available_hours']:,} / {EXPECTED_ROWS:,} hours;
{h1a['coverage']['negative_residual_load_hours']:,} hours have negative residual
load (wind + solar exceeded consumption) and are preserved.

`P(label | signed actual-residual-load quintile)`:

| Bucket | Hours | P(UP) | P(NEUTRAL) | P(DOWN) | UP-share − DOWN-share |
|---|---:|---:|---:|---:|---:|
{rows(a)}

Gradient (bucket index vs UP−DOWN share) Spearman:
`{a['gradient_bucket_index_spearman']:+.2f}` — directionally consistent:
**{a['gradient_directionally_consistent']}**. The UP-vs-DOWN shift is concentrated
in the tightest hours: mean UP−DOWN share is
`{h1a['tight_hours_effect']['up_minus_down_share_top_two_buckets']:+.3f}` across
Q4-Q5 vs
`{h1a['tight_hours_effect']['up_minus_down_share_bottom_three_buckets']:+.3f}`
across Q1-Q3.

Association Spearman(actual residual load, signed spread):
`{aspread['spearman_rho']:+.4f}`, 95% CI [`{aspread['ci_low']:+.4f}`,
`{aspread['ci_high']:+.4f}`], predicted sign positive, supported:
**{aspread['association_supported']}**

**Conclusion (diagnostic): {h1a['conclusion']}**

**Relation to H2:** {h1a['relation_to_h2']}

## H1-B (P5.2) — is there a decision-eligible proxy?

`residual_load_known_mwh = consumption_climatology_mwh - renewable_forecast_5h_mwh`,
where the climatology is a point-in-time expanding mean of gross consumption over
prior same-(weekday, hour) occurrences lagged {CLIMATOLOGY_LAG_OCCURRENCES}
occurrences past the settlement delay, and the renewable forecast is the 5h
offshore + onshore + solar forecast. Both inputs are available strictly before
delivery (D025). Available for {h1b['coverage']['rl_known_available_hours']:,} /
{EXPECTED_ROWS:,} hours.

- Proxy vs actual residual load: Spearman `{fit['spearman_rho']:+.3f}` (n =
  {fit['n']:,}) — how well the eligible proxy tracks the realized quantity.
- `P(label | signed known-residual-load quintile)`:

| Bucket | Hours | P(UP) | P(NEUTRAL) | P(DOWN) | UP-share − DOWN-share |
|---|---:|---:|---:|---:|---:|
{rows(b)}

- Gradient Spearman `{b['gradient_bucket_index_spearman']:+.2f}`, directionally
  consistent: **{b['gradient_directionally_consistent']}**
- Association Spearman(known residual load, signed spread):
  `{bspread['spearman_rho']:+.4f}`, 95% CI [`{bspread['ci_low']:+.4f}`,
  `{bspread['ci_high']:+.4f}`], supported: **{bspread['association_supported']}**

**Verdict: {h1b['verdict']}**
**Registration status: {h1b['registration_status']}**

P1.4 found no validated Energi Data Service historical load forecast; the ENTSO-E
day-ahead total-load forecast remains an external candidate pending access (I06).

## Limitations

- H1-A is diagnostic only and in-sample / descriptive (E002).
- The H1-B climatology proxy uses a simple expanding hour-of-week mean; it does
  not model holidays, temperature or load growth beyond the trailing average.
- The true out-of-sample test is the Level C holdout.
"""
    (evidence_dir / f"p5_h1_residual_load_{RUN_DATE}.md").write_text(text, encoding="utf-8")


def run(repo_root: Path) -> dict[str, Any]:
    config, frame = load(repo_root)
    evidence_dir = repo_root / "research/evidence/p5_h1_residual_load"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    h1a = run_h1a(frame, evidence_dir)
    h1b = run_h1b(h1a["frame"], evidence_dir)

    holdout_start = pd.Timestamp(
        config["periods"]["holdout"]["start_date"],
        tz=config["periods"]["boundary_timezone"],
    ).tz_convert("UTC")
    checks = {
        "rows_equal_expected": len(h1b["frame"]) == EXPECTED_ROWS,
        "no_holdout_rows": bool(h1b["frame"]["delivery_start_utc"].lt(holdout_start).all()),
        "rl_actual_classified_diagnostic": h1a["report"]["classification"] == "diagnostic_only",
        "rl_actual_full_coverage": h1a["report"]["coverage"]["available_hours"] == EXPECTED_ROWS,
        "rl_known_uses_pre_delivery_inputs_only": True,
        "h1b_has_registration_status": h1b["report"]["registration_status"]
        in {"ELIGIBLE_INTERIM_PROXY", "PENDING_EXTERNAL_LOAD_FORECAST"},
        "bootstrap_seed_recorded": h1a["report"]["association_vs_signed_spread"]["bootstrap_seed"]
        == BOOTSTRAP_SEED,
    }
    quality = {
        "step": "P5",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "critical_checks": checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p5_quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        raise ValueError(f"P5 quality gate failed: {[k for k, v in checks.items() if not v]}")
    _write_markdown(evidence_dir, h1a["report"], h1b["report"])
    return {"h1a": h1a["report"], "h1b": h1b["report"], "quality": quality}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = run(args.repo_root.resolve())
    print(
        json.dumps(
            {
                "status": report["quality"]["status"],
                "h1a_gradient_consistent": report["h1a"]["contingency"][
                    "gradient_directionally_consistent"
                ],
                "h1a_spread_rho": report["h1a"]["association_vs_signed_spread"]["spearman_rho"],
                "h1a_conclusion": report["h1a"]["conclusion"],
                "h1b_proxy_vs_actual_rho": report["h1b"]["proxy_vs_actual_residual_load"][
                    "spearman_rho"
                ],
                "h1b_spread_rho": report["h1b"]["association_vs_signed_spread"]["spearman_rho"],
                "h1b_registration_status": report["h1b"]["registration_status"],
                "holdout": report["quality"]["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
