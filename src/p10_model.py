"""P10.1 — logistic regression and calibration within development.

Fits a multinomial logistic regression on decision-eligible features against the
frozen three-class label, using a time-ordered development-only train /
calibration / validation split.  Calibration is fit only inside development.
The locked holdout is never read; this step produces the frozen model
specification and the test plan that P10.2 / P10.3 will execute.
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.p5_residual_load import build_rl_known


RUN_DATE = "2026-09-06"
EXPECTED_ROWS = 21_887
LABELS = ("UP", "DOWN", "NEUTRAL")

# --- pre-declared, time-ordered development-only split ---
TRAIN_END_LOCAL = "2023-07-01"        # train:        development start .. < this
CALIBRATION_END_LOCAL = "2024-01-01"  # calibration:  [TRAIN_END .. < this]
# validation: [CALIBRATION_END .. < holdout start (2024-07-01)]
CANDIDATE_C = (0.05, 0.1, 0.25, 0.5, 1.0)
RANDOM_STATE = 20260906

WIND_5H = ("forecast_5_hour_offshore_wind_mwh_per_hour", "forecast_5_hour_onshore_wind_mwh_per_hour")
FEATURES = (
    "wind_revision_mwh",
    "wind_forecast_5h_mwh",
    "wind_revision_when_low_wind_mwh",
    "solar_revision_mwh",
    "residual_load_known_mwh",
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
    "is_weekend",
)
LOW_WIND_CUT_MWH = 861.430541  # P4.4


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
    if holdout["state"] not in ("locked", "evaluated") or holdout["fetch_allowed"] is not False:
        raise ValueError("P10 requires the holdout to remain locked and fetch-disabled.")
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
        columns=["delivery_start_utc", "wind_revision_mwh", "solar_revision_mwh", "wind_revision_available"],
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


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    df = build_rl_known(frame).copy()
    df["wind_forecast_5h_mwh"] = df[list(WIND_5H)].sum(axis=1, min_count=2)
    df["wind_revision_when_low_wind_mwh"] = df["wind_revision_mwh"].where(
        df["wind_forecast_5h_mwh"] <= LOW_WIND_CUT_MWH, 0.0
    )
    hour = df["local_hour"].astype(float)
    doy = pd.to_datetime(df["local_date"]).dt.dayofyear.astype(float)
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["is_weekend"] = df["local_weekday"].isin(["Saturday", "Sunday"]).astype(float)
    df["feature_row_complete"] = df[list(FEATURES)].notna().all(axis=1) & df["target_label"].notna()
    return df


def _split_masks(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, pd.Series]:
    tz = config["periods"]["boundary_timezone"]
    t_end = pd.Timestamp(TRAIN_END_LOCAL, tz=tz).tz_convert("UTC")
    c_end = pd.Timestamp(CALIBRATION_END_LOCAL, tz=tz).tz_convert("UTC")
    h_start = pd.Timestamp(config["periods"]["holdout"]["start_date"], tz=tz).tz_convert("UTC")
    t = df["delivery_start_utc"]
    complete = df["feature_row_complete"]
    return {
        "train": complete & (t < t_end),
        "calibration": complete & (t >= t_end) & (t < c_end),
        "validation": complete & (t >= c_end) & (t < h_start),
    }


def _scores(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "n": int(len(y_true)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=list(LABELS), average="macro", zero_division=0)),
        "accuracy": float((y_true == y_pred).mean()),
    }


def _multiclass_brier(y_true: np.ndarray, proba: np.ndarray, classes: list[str]) -> float:
    onehot = np.zeros_like(proba)
    idx = {c: i for i, c in enumerate(classes)}
    for r, lab in enumerate(y_true):
        onehot[r, idx[lab]] = 1.0
    # sum-over-classes convention, range [0, 2] for three classes
    return float(np.mean(np.sum((proba - onehot) ** 2, axis=1)))


def _reliability_down(y_true: np.ndarray, p_down: np.ndarray) -> list[dict[str, Any]]:
    bins = np.linspace(0, 1, 11)
    out = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p_down >= lo) & (p_down < hi) if hi < 1 else (p_down >= lo) & (p_down <= hi)
        if m.sum() == 0:
            continue
        out.append({
            "bin": f"[{lo:.1f}, {hi:.1f})",
            "n": int(m.sum()),
            "mean_predicted_p_down": float(p_down[m].mean()),
            "observed_down_rate": float((y_true[m] == "DOWN").mean()),
        })
    return out


def run(repo_root: Path) -> dict[str, Any]:
    config, frame = load(repo_root)
    evidence_dir = repo_root / "research/evidence/p10_model"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    df = build_features(frame)
    masks = _split_masks(df, config)
    X = df[list(FEATURES)]
    y = df["target_label"].astype(str)

    scaler = StandardScaler().fit(X.loc[masks["train"]])

    def Xs(mask: pd.Series) -> np.ndarray:
        return scaler.transform(X.loc[mask])

    ytr = y.loc[masks["train"]].to_numpy()
    ycal = y.loc[masks["calibration"]].to_numpy()
    yval = y.loc[masks["validation"]].to_numpy()

    # model selection on the calibration slice (macro-F1), pre-declared C grid
    selection = []
    best = None
    for c in CANDIDATE_C:
        lr = LogisticRegression(
            C=c, class_weight="balanced", max_iter=5000, random_state=RANDOM_STATE
        ).fit(Xs(masks["train"]), ytr)
        pred_cal = lr.predict(Xs(masks["calibration"]))
        macro = float(f1_score(ycal, pred_cal, labels=list(LABELS), average="macro", zero_division=0))
        selection.append({"C": c, "calibration_macro_f1": macro})
        if best is None or macro > best[1]:
            best = (c, macro, lr)
    best_c, _best_macro, best_lr = best

    calib_candidates = {}
    for method in ("sigmoid", "isotonic"):
        cc = CalibratedClassifierCV(FrozenEstimator(best_lr), method=method).fit(
            Xs(masks["calibration"]), ycal
        )
        proba = cc.predict_proba(Xs(masks["validation"]))
        calib_candidates[method] = (
            cc,
            _multiclass_brier(yval, proba, list(cc.classes_)),
        )
    calibration_method = min(calib_candidates, key=lambda m: calib_candidates[m][1])
    calibrated = calib_candidates[calibration_method][0]
    classes = list(calibrated.classes_)

    val_pred_raw = best_lr.predict(Xs(masks["validation"]))
    val_proba_raw = best_lr.predict_proba(Xs(masks["validation"]))
    val_pred_cal = calibrated.predict(Xs(masks["validation"]))
    val_proba_cal = calibrated.predict_proba(Xs(masks["validation"]))

    # baselines fit on train, evaluated on validation
    train_majority = pd.Series(ytr).value_counts().idxmax()
    how_map = (
        df.loc[masks["train"]]
        .groupby(["local_weekday", "local_hour"])["target_label"]
        .agg(lambda s: s.value_counts().idxmax())
        .to_dict()
    )
    val_rows = df.loc[masks["validation"]]
    how_pred = np.array(
        [how_map.get((w, h), train_majority) for w, h in zip(val_rows["local_weekday"], val_rows["local_hour"])]
    )
    prev_label = df["target_label"].shift(1)
    prev_time = df["delivery_start_utc"].shift(1)
    consecutive = (df["delivery_start_utc"] - prev_time).eq(pd.Timedelta(hours=1))
    persistence_all = prev_label.where(consecutive)
    pers_mask = masks["validation"] & persistence_all.notna()

    coefs = {
        cls: {feat: float(w) for feat, w in zip(FEATURES, row)}
        for cls, row in zip(classes, np.atleast_2d(best_lr.coef_))
    }

    p_down_cal = val_proba_cal[:, classes.index("DOWN")]

    coef_signs = {}
    expected = {
        ("DOWN", "wind_revision_mwh"): "+",
        ("DOWN", "wind_forecast_5h_mwh"): "-",
        ("DOWN", "residual_load_known_mwh"): "-",
        ("UP", "wind_revision_mwh"): "-",
        ("UP", "residual_load_known_mwh"): "+",
    }
    for (cls, feat), want in expected.items():
        got = coefs[cls][feat]
        coef_signs[f"{cls}:{feat}"] = {
            "coefficient": round(got, 3),
            "expected_sign": want,
            "matches": (got > 0) == (want == "+"),
        }

    raw = _scores(yval, val_pred_raw)
    cal = _scores(yval, val_pred_cal)
    maj = _scores(yval, np.full(len(yval), train_majority))
    validation_conclusion = (
        "The coefficient signs match the H1/H2 mechanisms for "
        f"{sum(v['matches'] for v in coef_signs.values())} of {len(coef_signs)} checked terms, "
        "but on the 2024 H1 development validation slice there is no edge: the "
        f"class-weighted argmax reaches balanced accuracy {raw['balanced_accuracy']:.3f} "
        f"(vs 0.333 chance), and after calibration the argmax collapses to the majority "
        f"class ({cal['balanced_accuracy']:.3f}, equal to majority {maj['balanced_accuracy']:.3f}). "
        "Calibrated probabilities are no better than train-frequency climatology on this slice. "
        "This is consistent with P4.4 -- 2024 H1 is where the H2 gradient did not reproduce. "
        "The Level C holdout report will present both the raw and the calibrated predictions."
    )

    report = {
        "step": "P10.1",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_run": git_head(repo_root),
        "scope": "development only; model and calibration fit inside development; holdout not read",
        "frozen_specification": {
            "model": "multinomial LogisticRegression (lbfgs), class_weight=balanced",
            "features": list(FEATURES),
            "standardization": "StandardScaler fit on the train slice only",
            "selected_C": best_c,
            "candidate_C_grid": list(CANDIDATE_C),
            "random_state": RANDOM_STATE,
            "calibration": f"{calibration_method}, CalibratedClassifierCV on the frozen model, fit on the calibration slice only (selected as the lower-Brier of sigmoid and isotonic)",
            "calibration_brier_candidates_validation": {m: v[1] for m, v in calib_candidates.items()},
            "target": "frozen three-class label (D026); delta not re-estimated",
        },
        "temporal_split": {
            "train": {"rule": f"development start .. < {TRAIN_END_LOCAL} local", "n": int(masks["train"].sum())},
            "calibration": {"rule": f"[{TRAIN_END_LOCAL} .. < {CALIBRATION_END_LOCAL}) local", "n": int(masks["calibration"].sum())},
            "validation": {"rule": f"[{CALIBRATION_END_LOCAL} .. < 2024-07-01) local", "n": int(masks["validation"].sum())},
            "feature_complete_rows": int(df["feature_row_complete"].sum()),
            "rows_dropped_incomplete_features": int((~df["feature_row_complete"]).sum()),
        },
        "model_selection": selection,
        "coefficients_standardized": coefs,
        "coefficient_sign_checks": coef_signs,
        "validation_conclusion": validation_conclusion,
        "validation_performance": {
            "logistic_raw": _scores(yval, val_pred_raw),
            "logistic_calibrated": _scores(yval, val_pred_cal),
            "majority_train": _scores(yval, np.full(len(yval), train_majority)),
            "hour_of_week_train": _scores(yval, how_pred),
            "persistence_ex_post": _scores(
                y.loc[pers_mask].to_numpy(), persistence_all.loc[pers_mask].to_numpy()
            ),
        },
        "probability_quality_validation": {
            "brier_convention": "mean sum_k (p_k - y_k)^2, range [0, 2] for three classes",
            "multiclass_brier_raw": _multiclass_brier(yval, val_proba_raw, classes),
            "multiclass_brier_calibrated": _multiclass_brier(yval, val_proba_cal, classes),
            "reference_brier_train_class_frequencies": _multiclass_brier(
                yval,
                np.tile(
                    pd.Series(ytr).value_counts(normalize=True).reindex(classes).to_numpy(),
                    (len(yval), 1),
                ),
                classes,
            ),
            "down_class_reliability_calibrated": _reliability_down(yval, p_down_cal),
        },
        "p10_2_p10_3_test_plan": {
            "freeze": "this specification (features, C, calibration, split dates, target labels, delta 5.9956075)",
            "unlock_gate": "record the unlock date, frozen code/config version, prior-non-use evidence and planned request boundaries in the decision log holdout-unlock template",
            "holdout_request": "local 2024-07-01 00:00 inclusive to 2025-01-01 00:00 exclusive, DK1 only, same sources and pipeline",
            "primary_report": "calibrated logistic vs majority and hour-of-week (both fit on all development) on balanced accuracy, macro-F1 and multiclass Brier; persistence reported as ex-post reference",
            "secondary": "by-season and by-wind-level performance; the P7 transparent rule for comparison; Q20/Q30 delta sensitivity as pre-declared secondaries",
            "protocol_for_changes_after_inspection": "any change informed by the holdout is exploratory and needs fresh unseen data",
        },
        "holdout": "LOCKED_AND_UNUSED",
    }

    chart_path = evidence_dir / f"p10_1_calibration_chart_{RUN_DATE}.png"
    _calibration_chart(report["probability_quality_validation"]["down_class_reliability_calibrated"], chart_path)
    json_dump(evidence_dir / f"p10_1_model_{RUN_DATE}.json", report)

    checks = {
        "rows_equal_expected": len(df) == EXPECTED_ROWS,
        "splits_are_time_ordered_and_disjoint": (
            masks["train"].sum() > 0
            and masks["calibration"].sum() > 0
            and masks["validation"].sum() > 0
            and int((masks["train"] & masks["calibration"]).sum()) == 0
            and int((masks["calibration"] & masks["validation"]).sum()) == 0
        ),
        "no_holdout_rows_in_any_split": bool(
            df.loc[masks["train"] | masks["calibration"] | masks["validation"], "delivery_start_utc"].lt(
                pd.Timestamp(config["periods"]["holdout"]["start_date"],
                             tz=config["periods"]["boundary_timezone"]).tz_convert("UTC")
            ).all()
        ),
        "calibration_improves_or_holds_brier": report["probability_quality_validation"][
            "multiclass_brier_calibrated"
        ] <= report["probability_quality_validation"]["multiclass_brier_raw"] + 1e-6,
        "features_are_decision_eligible": set(FEATURES).isdisjoint(
            {"balancing_spread_eur_mwh", "target_label", "imbalance_price_eur_mwh", "residual_load_actual_mwh"}
        ),
        "delta_not_re_estimated": float(config["neutral_band"]["numerical_delta"]) == 5.9956075,
        "test_plan_recorded": "unlock_gate" in report["p10_2_p10_3_test_plan"],
        "chart_written": chart_path.exists(),
    }
    quality = {
        "step": "P10.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "critical_checks": checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    json_dump(evidence_dir / f"p10_1_quality_report_{RUN_DATE}.json", quality)
    if quality["status"] != "PASS":
        raise ValueError(f"P10.1 quality gate failed: {[k for k, v in checks.items() if not v]}")
    _write_markdown(evidence_dir, report)
    return {"report": report, "quality": quality}


def _calibration_chart(reliability: list[dict[str, Any]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ax.plot([0, 0.6], [0, 0.6], color="#8b909b", linestyle="--", linewidth=1, label="perfect")
    xs = [r["mean_predicted_p_down"] for r in reliability]
    ys = [r["observed_down_rate"] for r in reliability]
    ns = [r["n"] for r in reliability]
    ax.plot(xs, ys, color="#3a6ea6", marker="o", linewidth=2)
    for x, y, n in zip(xs, ys, ns):
        ax.annotate(f"n={n}", (x, y), textcoords="offset points", xytext=(6, -4), fontsize=8, color="#6b7484")
    ax.set_xlabel("Mean predicted P(DOWN), calibrated")
    ax.set_ylabel("Observed DOWN rate")
    ax.set_title("P10.1 calibration — DOWN class, development validation slice\n(2024-01-01 to 2024-06-30, holdout still locked)")
    ax.set_xlim(0, max(0.6, max(xs) + 0.05))
    ax.set_ylim(0, max(0.6, max(ys) + 0.05))
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _write_markdown(evidence_dir: Path, r: dict[str, Any]) -> None:
    sp = r["temporal_split"]
    vp = r["validation_performance"]
    pq = r["probability_quality_validation"]
    spec = r["frozen_specification"]
    text = f"""# P10.1 — Logistic Regression and Calibration (development only)

**Status:** complete — {RUN_DATE}
**Scope:** model and calibration fit inside development; **the holdout is not read**
**Holdout:** LOCKED AND UNUSED

## Frozen specification

- Model: {spec['model']}; selected `C = {spec['selected_C']}` from
  {spec['candidate_C_grid']} by calibration-slice macro-F1 (the grid is nearly
  flat — the features carry little signal).
- Calibration: {spec['calibration']}.
- Features (decision-eligible): {spec['features']}.
- Target: the frozen three-class label; `delta = 5.9956075` is **not**
  re-estimated.

## Time-ordered development split

| Slice | Rule | Rows |
|---|---|---:|
| Train | {sp['train']['rule']} | {sp['train']['n']:,} |
| Calibration | {sp['calibration']['rule']} | {sp['calibration']['n']:,} |
| Validation | {sp['validation']['rule']} | {sp['validation']['n']:,} |

{sp['rows_dropped_incomplete_features']:,} of {EXPECTED_ROWS:,} hours dropped for an
incomplete feature row.

## What the model learned

Standardized coefficient sign checks against the H1 / H2 mechanisms:

| Term | Coefficient | Expected | Matches |
|---|---:|:--:|:--:|
""" + "\n".join(
        f"| {k} | {v['coefficient']:+.3f} | {v['expected_sign']} | {'yes' if v['matches'] else 'NO'} |"
        for k, v in r["coefficient_sign_checks"].items()
    ) + f"""

**{r['validation_conclusion']}**

## Validation performance

| Method | Balanced acc. | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| Logistic (calibrated) | {vp['logistic_calibrated']['balanced_accuracy']:.3f} | {vp['logistic_calibrated']['macro_f1']:.3f} | {vp['logistic_calibrated']['accuracy']:.3f} |
| Logistic (raw) | {vp['logistic_raw']['balanced_accuracy']:.3f} | {vp['logistic_raw']['macro_f1']:.3f} | {vp['logistic_raw']['accuracy']:.3f} |
| Majority (train) | {vp['majority_train']['balanced_accuracy']:.3f} | {vp['majority_train']['macro_f1']:.3f} | {vp['majority_train']['accuracy']:.3f} |
| Hour-of-week (train) | {vp['hour_of_week_train']['balanced_accuracy']:.3f} | {vp['hour_of_week_train']['macro_f1']:.3f} | {vp['hour_of_week_train']['accuracy']:.3f} |
| Persistence (ex-post) | {vp['persistence_ex_post']['balanced_accuracy']:.3f} | {vp['persistence_ex_post']['macro_f1']:.3f} | {vp['persistence_ex_post']['accuracy']:.3f} |

## Probability quality (validation)

Multiclass Brier ({pq['brier_convention']}):
raw `{pq['multiclass_brier_raw']:.4f}`, calibrated
`{pq['multiclass_brier_calibrated']:.4f}`, train-frequency reference
`{pq['reference_brier_train_class_frequencies']:.4f}`. Calibration curve for the
DOWN class: `p10_1_calibration_chart_{RUN_DATE}.png`.

## P10.2 / P10.3 test plan

- **Freeze** this specification and the frozen target.
- **Unlock gate:** complete the decision-log holdout-unlock template — unlock
  date, frozen code/config version, prior-non-use evidence, planned request
  boundaries.
- **Holdout request:** local 2024-07-01 00:00 inclusive to 2025-01-01 00:00
  exclusive, DK1, same sources and pipeline.
- **Primary report:** calibrated logistic vs majority and hour-of-week (fit on
  all development) on balanced accuracy, macro-F1 and multiclass Brier;
  persistence as an ex-post reference; the P7 transparent rule for comparison.
- **Secondary:** by-season and by-wind-level performance; Q20 / Q30 delta
  sensitivity.
- Any change informed by the holdout is exploratory and needs fresh unseen data.

## Limitations

- Development-only. The validation slice is 2024 H1 — the same window where the
  H2 gradient did not reproduce (P4.4), so a weak validation result is expected
  and is itself informative.
- The model inherits every upstream weakness (small effect sizes, no
  demand-shock information).
"""
    (evidence_dir / f"p10_1_model_{RUN_DATE}.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    out = run(args.repo_root.resolve())
    r = out["report"]
    vp = r["validation_performance"]
    print(
        json.dumps(
            {
                "status": out["quality"]["status"],
                "selected_C": r["frozen_specification"]["selected_C"],
                "validation_n": r["temporal_split"]["validation"]["n"],
                "logistic_calibrated_balanced_accuracy": vp["logistic_calibrated"]["balanced_accuracy"],
                "hour_of_week_balanced_accuracy": vp["hour_of_week_train"]["balanced_accuracy"],
                "brier_raw": r["probability_quality_validation"]["multiclass_brier_raw"],
                "brier_calibrated": r["probability_quality_validation"]["multiclass_brier_calibrated"],
                "holdout": r["holdout"],
            }
        )
    )


if __name__ == "__main__":
    main()
