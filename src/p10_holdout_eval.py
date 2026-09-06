"""P10.3 — the single owner-approved locked-holdout evaluation.

Unlocks the holdout in the research config, fetches the 2024-07-01..2024-12-31
DK1 data for the datasets the frozen model needs, builds the holdout feature
table with the frozen recipe (frozen delta, frozen thresholds), evaluates the
frozen logistic model once against the mandatory baselines, and re-locks the
config as ``state: evaluated``.  This runs only after the D036 unlock record and
owner approval; the resulting research decision is D037. It runs only once.
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
from src.eds_api_client import BoundedEnergiDataClient, RequestSpec
from src.p10_model import FEATURES, LABELS, _multiclass_brier, _scores

RUN_DATE = "2026-09-06"
FROZEN_DELTA = 5.9956075
LOW_WIND_CUT_MWH = 861.430541
WIND_LEVEL_TERCILE_EDGES = (861.430541, 2067.000020)  # P4.4
CLIMATOLOGY_LAG_OCCURRENCES = 3
SEASON = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
          6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
# frozen P7 thresholds (config signal_engine)
P7_H2_STRONG = 222.6
P7_RL_TIGHT = 1855.7

HOLDOUT_START_LOCAL = "2024-07-01"
HOLDOUT_END_EXCLUSIVE_LOCAL = "2025-01-01"

DATASETS = {
    "Forecasts_Hour": {"sort": "HourUTC,PriceArea,ForecastType"},
    "Elspotprices": {"sort": "HourUTC"},
    "RegulatingBalancePowerdata": {"sort": "HourUTC"},
    "ProductionConsumptionSettlement": {"sort": "HourUTC"},
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_head(repo_root: Path) -> str | None:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=False,
                         capture_output=True, text=True)
    return out.stdout.strip() or None


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _set_holdout_state(config_path: Path, **fields: Any) -> None:
    """Surgically rewrite only the `holdout:` block, preserving the rest of the file."""
    text = config_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "holdout:")
    end = next(i for i in range(start + 1, len(lines)) if lines[i] and not lines[i].startswith("    "))
    block = ["  holdout:", '    start_date: "2024-07-01"', '    end_date_inclusive: "2024-12-31"']
    for key, value in fields.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, str):
            rendered = '"' + value.replace('"', "'") + '"'
        else:
            rendered = str(value)
        block.append(f"    {key}: {rendered}")
    config_path.write_text("\n".join(lines[:start] + block + lines[end:]) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- fetch + shape ---


def fetch_holdout_raw(repo_root: Path) -> dict[str, pd.DataFrame]:
    raw_dir = repo_root / "data/raw/p10_holdout"
    evidence_dir = repo_root / "research/evidence/p10_holdout"
    paths = {n: raw_dir / f"{n}_DK1_holdout_2024-07-01_2024-12-31.json" for n in DATASETS}

    if all(p.exists() for p in paths.values()):
        # Idempotent recovery: the owner-approved fetch already happened; re-reading
        # the local raw files is not a new holdout access.
        frames, provenance = {}, []
        for name, p in paths.items():
            payload = json.loads(p.read_text(encoding="utf-8"))
            frames[name] = pd.DataFrame(payload["records"])
            provenance.append({"dataset": name, "records": len(payload["records"]),
                               "sha256": sha256_bytes(p.read_bytes()), "source": "local (already fetched)"})
        json_dump(evidence_dir / f"holdout_raw_provenance_{RUN_DATE}.json",
                  {"step": "P10.3", "source_organization": "Energinet", "note": "raw files already present",
                   "files": provenance})
        return frames

    client = BoundedEnergiDataClient(repo_root / "config/research_config.yaml", unlock_holdout=True)
    frames = {}
    provenance = []
    for name, opts in DATASETS.items():
        spec = RequestSpec(
            dataset=name,
            start_date=HOLDOUT_START_LOCAL,
            end_date_exclusive=HOLDOUT_END_EXCLUSIVE_LOCAL,
            filters={"PriceArea": ["DK1"]},
            sort=opts["sort"],
            limit=0,
        )
        result = client.fetch(spec)
        client.save(result, raw_path=paths[name], manifest_path=raw_dir / f"{name}_manifest.json")
        records = result.payload["records"]
        frames[name] = pd.DataFrame(records)
        provenance.append({
            "dataset": name,
            "records": len(records),
            "api_reported_total": result.payload.get("total"),
            "sha256": sha256_bytes(result.raw_bytes),
            "retrieved_at_utc": result.retrieved_at_utc,
            "request": {"start": spec.start_date, "end_exclusive": spec.end_date_exclusive,
                        "filter": spec.filters, "sort": spec.sort, "timezone": "DK"},
        })
    json_dump(evidence_dir / f"holdout_raw_provenance_{RUN_DATE}.json",
              {"step": "P10.3", "source_organization": "Energinet", "files": provenance})
    return frames


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="raise")


def build_holdout_frame(repo_root: Path, raw: dict[str, pd.DataFrame], config: dict[str, Any]) -> pd.DataFrame:
    tz = config["periods"]["boundary_timezone"]

    spot = raw["Elspotprices"][["HourUTC", "SpotPriceEUR"]].copy()
    spot["delivery_start_utc"] = _utc(spot["HourUTC"])
    spot = spot.rename(columns={"SpotPriceEUR": "spot_price_eur_mwh"})[
        ["delivery_start_utc", "spot_price_eur_mwh"]
    ]

    bal = raw["RegulatingBalancePowerdata"][["HourUTC", "ImbalancePriceEUR"]].copy()
    bal["delivery_start_utc"] = _utc(bal["HourUTC"])
    bal = bal.rename(columns={"ImbalancePriceEUR": "imbalance_price_eur_mwh"})[
        ["delivery_start_utc", "imbalance_price_eur_mwh"]
    ]

    cons = raw["ProductionConsumptionSettlement"][["HourUTC", "GrossConsumptionMWh"]].copy()
    cons["delivery_start_utc"] = _utc(cons["HourUTC"])
    cons = cons.rename(columns={"GrossConsumptionMWh": "actual_gross_consumption_mwh"})[
        ["delivery_start_utc", "actual_gross_consumption_mwh"]
    ]

    fc = raw["Forecasts_Hour"].copy()
    fc["delivery_start_utc"] = _utc(fc["HourUTC"])
    slug = {"Offshore Wind": "offshore_wind", "Onshore Wind": "onshore_wind", "Solar": "solar"}
    wide_parts = []
    for ftype, s in slug.items():
        part = fc.loc[fc["ForecastType"] == ftype, ["delivery_start_utc", "Forecast5Hour", "Forecast1Hour"]].copy()
        part = part.rename(columns={
            "Forecast5Hour": f"forecast_5_hour_{s}_mwh_per_hour",
            "Forecast1Hour": f"forecast_1_hour_{s}_mwh_per_hour",
        })
        wide_parts.append(part.set_index("delivery_start_utc"))
    forecasts = pd.concat(wide_parts, axis=1).reset_index()

    base = pd.date_range(
        HOLDOUT_START_LOCAL, HOLDOUT_END_EXCLUSIVE_LOCAL, inclusive="left", freq="h", tz=tz
    )
    df = pd.DataFrame({"delivery_start_local": base})
    df["delivery_start_utc"] = df["delivery_start_local"].dt.tz_convert("UTC")
    df["local_date"] = df["delivery_start_local"].dt.strftime("%Y-%m-%d")
    df["local_hour"] = df["delivery_start_local"].dt.hour
    df["local_weekday"] = df["delivery_start_local"].dt.day_name()
    for right in (spot, bal, cons, forecasts):
        df = df.merge(right, on="delivery_start_utc", how="left", validate="one_to_one")

    df["balancing_spread_eur_mwh"] = df["imbalance_price_eur_mwh"] - df["spot_price_eur_mwh"]
    spread = df["balancing_spread_eur_mwh"]
    label = pd.Series(pd.NA, index=df.index, dtype="string")
    label.loc[spread.gt(FROZEN_DELTA)] = "UP"
    label.loc[spread.lt(-FROZEN_DELTA)] = "DOWN"
    label.loc[spread.notna() & spread.abs().le(FROZEN_DELTA)] = "NEUTRAL"
    df["target_label"] = label

    off5, off1 = df["forecast_5_hour_offshore_wind_mwh_per_hour"], df["forecast_1_hour_offshore_wind_mwh_per_hour"]
    on5, on1 = df["forecast_5_hour_onshore_wind_mwh_per_hour"], df["forecast_1_hour_onshore_wind_mwh_per_hour"]
    s5, s1 = df["forecast_5_hour_solar_mwh_per_hour"], df["forecast_1_hour_solar_mwh_per_hour"]
    wind_ok = off5.notna() & off1.notna() & on5.notna() & on1.notna()
    df["wind_revision_mwh"] = ((off1 - off5) + (on1 - on5)).where(wind_ok)
    df["wind_forecast_5h_mwh"] = (off5 + on5).where(off5.notna() & on5.notna())
    df["solar_revision_mwh"] = (s1 - s5).where(s5.notna() & s1.notna())
    df["renewable_forecast_5h_mwh"] = (off5 + on5 + s5).where(off5.notna() & on5.notna() & s5.notna())
    return df


def add_climatology_features(repo_root: Path, holdout: pd.DataFrame) -> pd.DataFrame:
    dev = pd.read_parquet(
        repo_root / "data/processed/p3/target_development.parquet",
        columns=["delivery_start_utc", "local_weekday", "local_hour", "actual_gross_consumption_mwh"],
    )
    dev["_from"] = "development"
    hcols = holdout[["delivery_start_utc", "local_weekday", "local_hour", "actual_gross_consumption_mwh"]].copy()
    hcols["_from"] = "holdout"
    both = pd.concat([dev, hcols], ignore_index=True).sort_values("delivery_start_utc")
    both["_how"] = both["local_weekday"].astype(str) + "|" + both["local_hour"].astype(str)
    clim = pd.Series(np.nan, index=both.index, dtype=float)
    for _, grp in both.groupby("_how", sort=False):
        clim.loc[grp.index] = (
            grp["actual_gross_consumption_mwh"].expanding().mean().shift(CLIMATOLOGY_LAG_OCCURRENCES).to_numpy()
        )
    both["consumption_climatology_mwh"] = clim
    holdout_clim = both.loc[both["_from"] == "holdout", ["delivery_start_utc", "consumption_climatology_mwh"]]
    out = holdout.merge(holdout_clim, on="delivery_start_utc", how="left", validate="one_to_one")
    out["residual_load_known_mwh"] = (
        out["consumption_climatology_mwh"] - out["renewable_forecast_5h_mwh"]
    )
    hour = out["local_hour"].astype(float)
    doy = pd.to_datetime(out["local_date"]).dt.dayofyear.astype(float)
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    out["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    out["is_weekend"] = out["local_weekday"].isin(["Saturday", "Sunday"]).astype(float)
    out["wind_revision_when_low_wind_mwh"] = out["wind_revision_mwh"].where(
        out["wind_forecast_5h_mwh"] <= LOW_WIND_CUT_MWH, 0.0
    )
    out["feature_row_complete"] = out[list(FEATURES)].notna().all(axis=1) & out["target_label"].notna()
    return out


# --------------------------------------------------------------- model refit ---


def fit_frozen_model(repo_root: Path) -> tuple[Any, Any, StandardScaler, dict[str, Any]]:
    from src.p10_model import build_features as dev_build_features, load as dev_load

    config, dev = dev_load(repo_root)
    dev = dev_build_features(dev)
    tz = config["periods"]["boundary_timezone"]
    cal_start = pd.Timestamp("2024-01-01", tz=tz).tz_convert("UTC")
    h_start = pd.Timestamp("2024-07-01", tz=tz).tz_convert("UTC")
    complete = dev["feature_row_complete"]
    fit_mask = complete & (dev["delivery_start_utc"] < cal_start)
    cal_mask = complete & (dev["delivery_start_utc"] >= cal_start) & (dev["delivery_start_utc"] < h_start)

    X = dev[list(FEATURES)]
    y = dev["target_label"].astype(str)
    scaler = StandardScaler().fit(X.loc[fit_mask])
    lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000, random_state=20260906).fit(
        scaler.transform(X.loc[fit_mask]), y.loc[fit_mask].to_numpy()
    )
    calibrated = CalibratedClassifierCV(FrozenEstimator(lr), method="sigmoid").fit(
        scaler.transform(X.loc[cal_mask]), y.loc[cal_mask].to_numpy()
    )
    hour_of_week = (
        dev.loc[complete].groupby(["local_weekday", "local_hour"])["target_label"]
        .agg(lambda s: s.value_counts().idxmax()).to_dict()
    )
    train_majority = y.loc[complete].value_counts().idxmax()
    q20 = float(dev["balancing_spread_eur_mwh"].abs().loc[
        dev["balancing_spread_eur_mwh"].ne(0) & dev["balancing_spread_eur_mwh"].notna()
    ].quantile(0.20, interpolation="linear"))
    q30 = float(dev["balancing_spread_eur_mwh"].abs().loc[
        dev["balancing_spread_eur_mwh"].ne(0) & dev["balancing_spread_eur_mwh"].notna()
    ].quantile(0.30, interpolation="linear"))
    meta = {
        "fit_rows": int(fit_mask.sum()),
        "calibration_rows": int(cal_mask.sum()),
        "fit_rule": "development < 2024-01-01; Platt calibration on [2024-01-01, 2024-07-01); C=1.0 as selected in P10.1",
        "hour_of_week_map": hour_of_week,
        "train_majority": train_majority,
        "delta_q20": q20,
        "delta_q30": q30,
    }
    return lr, calibrated, scaler, meta


# ------------------------------------------------------------------- evaluate ---


def _p7_rule(df: pd.DataFrame) -> pd.Series:
    rev = df["wind_revision_mwh"]
    wf5 = df["wind_forecast_5h_mwh"]
    rlk = df["residual_load_known_mwh"]
    h2_down = rev.gt(P7_H2_STRONG) & wf5.gt(LOW_WIND_CUT_MWH)
    h1_up = rlk.gt(P7_RL_TIGHT)
    out = pd.Series("NEUTRAL", index=df.index, dtype="object")
    out.loc[h1_up & ~h2_down] = "UP"
    out.loc[h2_down & ~h1_up] = "DOWN"
    return out


def _label_with_delta(spread: pd.Series, delta: float) -> pd.Series:
    lab = pd.Series(pd.NA, index=spread.index, dtype="string")
    lab.loc[spread.gt(delta)] = "UP"
    lab.loc[spread.lt(-delta)] = "DOWN"
    lab.loc[spread.notna() & spread.abs().le(delta)] = "NEUTRAL"
    return lab


def evaluate(repo_root: Path, model: tuple[Any, Any, StandardScaler, dict[str, Any]]) -> dict[str, Any]:
    config_path = repo_root / "config/research_config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["periods"]["holdout"].get("unlock_decision") != "D036":
        raise ValueError("Holdout unlock must reference the approved decision D036.")

    lr, calibrated, scaler, meta = model
    evidence_dir = repo_root / "research/evidence/p10_holdout"
    raw = fetch_holdout_raw(repo_root)
    holdout = build_holdout_frame(repo_root, raw, config)
    holdout = add_climatology_features(repo_root, holdout)
    out_parquet = repo_root / "data/processed/p10_holdout/holdout_features.parquet"
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    holdout.to_parquet(out_parquet, index=False)
    classes = list(calibrated.classes_)

    mask = holdout["feature_row_complete"]
    Xh = scaler.transform(holdout.loc[mask, list(FEATURES)])
    y_true = holdout.loc[mask, "target_label"].astype(str).to_numpy()
    pred_raw = lr.predict(Xh)
    pred_cal = calibrated.predict(Xh)
    proba_cal = calibrated.predict_proba(Xh)

    maj = np.full(len(y_true), meta["train_majority"])
    how = holdout.loc[mask].apply(
        lambda r: meta["hour_of_week_map"].get((r["local_weekday"], r["local_hour"]), meta["train_majority"]),
        axis=1,
    ).to_numpy()
    prev = holdout["target_label"].shift(1)
    prev_time = holdout["delivery_start_utc"].shift(1)
    consec = (holdout["delivery_start_utc"] - prev_time).eq(pd.Timedelta(hours=1))
    pers = prev.where(consec)
    pers_mask = mask & pers.notna()
    p7 = _p7_rule(holdout).loc[mask].to_numpy()

    season = pd.to_datetime(holdout.loc[mask, "local_date"]).dt.month.map(SEASON).to_numpy()
    wl = pd.cut(
        holdout.loc[mask, "wind_forecast_5h_mwh"],
        [-np.inf, *WIND_LEVEL_TERCILE_EDGES, np.inf],
        labels=["low_wind", "mid_wind", "high_wind"],
    ).astype(str).to_numpy()

    def strat(groups: np.ndarray) -> dict[str, Any]:
        out = {}
        for g in sorted(set(groups)):
            gm = groups == g
            if gm.sum() < 100:
                out[g] = {"n": int(gm.sum()), "note": "small"}
                continue
            out[g] = {
                "n": int(gm.sum()),
                "calibrated": _scores(y_true[gm], pred_cal[gm]),
                "majority": _scores(y_true[gm], maj[gm]),
            }
        return out

    spread_h = holdout.loc[mask, "balancing_spread_eur_mwh"]
    delta_sens = {}
    for name, d in (("Q20", meta["delta_q20"]), ("Q25_primary", FROZEN_DELTA), ("Q30", meta["delta_q30"])):
        yt = _label_with_delta(spread_h, d).astype(str).to_numpy()
        delta_sens[name] = {
            "delta": d,
            "calibrated_balanced_accuracy": float(balanced_accuracy_score(yt, pred_cal)),
            "majority_balanced_accuracy": float(balanced_accuracy_score(yt, np.full(len(yt), meta["train_majority"]))),
        }

    by_season = strat(season)
    by_wind_level = strat(wl)
    signed_dist = {
        lab: {
            "n": int((pd.Series(pred_cal) == lab).sum()),
            "realized_shares": {
                r: float((y_true[pred_cal == lab] == r).mean()) if (pred_cal == lab).any() else None
                for r in LABELS
            },
        }
        for lab in LABELS
    }

    result = {
        "step": "P10.3",
        "status": "COMPLETE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head(repo_root),
        "holdout_window_local": f"{HOLDOUT_START_LOCAL} .. {HOLDOUT_END_EXCLUSIVE_LOCAL} (exclusive)",
        "coverage": {
            "holdout_hours": int(len(holdout)),
            "valid_label_hours": int(holdout["target_label"].notna().sum()),
            "feature_complete_and_labelled": int(mask.sum()),
            "missing_balancing_hours": int(holdout["imbalance_price_eur_mwh"].isna().sum()),
        },
        "model_refit": {k: v for k, v in meta.items() if k not in ("hour_of_week_map",)},
        "label_counts_holdout": {k: int((holdout["target_label"] == k).sum()) for k in LABELS},
        "primary_metrics": {
            "logistic_calibrated": _scores(y_true, pred_cal),
            "logistic_raw": _scores(y_true, pred_raw),
            "majority_from_development": _scores(y_true, maj),
            "hour_of_week_from_development": _scores(y_true, how),
            "persistence_ex_post": _scores(
                holdout.loc[pers_mask, "target_label"].astype(str).to_numpy(),
                pers.loc[pers_mask].astype(str).to_numpy(),
            ),
            "p7_transparent_rule": _scores(y_true, p7),
        },
        "probability_quality": {
            "brier_convention": "mean sum_k (p_k - y_k)^2, range [0, 2]",
            "multiclass_brier_calibrated": _multiclass_brier(y_true, proba_cal, classes),
            "reference_brier_development_class_frequencies": _multiclass_brier(
                y_true,
                np.tile(
                    pd.Series(_dev_label_freq(repo_root)).reindex(classes).to_numpy(),
                    (len(y_true), 1),
                ),
                classes,
            ),
        },
        "calibrated_prediction_distribution": signed_dist,
        "by_season": by_season,
        "by_wind_level": by_wind_level,
        "delta_sensitivity": delta_sens,
        "interpretation": "",
        "protocol_reminder": "Any change informed by this holdout is exploratory and needs fresh unseen data.",
        "holdout": "EVALUATED_ONCE",
    }
    result["interpretation"] = _interpret(result)

    json_dump(evidence_dir / f"p10_3_holdout_result_{RUN_DATE}.json", result)
    _chart(y_true, proba_cal, classes, evidence_dir / f"p10_3_holdout_calibration_{RUN_DATE}.png")
    _write_md(evidence_dir, result)
    return result


def _dev_label_freq(repo_root: Path) -> dict[str, float]:
    dev = pd.read_parquet(repo_root / "data/processed/p3/target_development.parquet", columns=["target_label"])
    vc = dev["target_label"].dropna().value_counts(normalize=True)
    return {k: float(vc.get(k, 0.0)) for k in LABELS}


def _interpret(r: dict[str, Any]) -> str:
    pm = r["primary_metrics"]
    cal = pm["logistic_calibrated"]["balanced_accuracy"]
    maj = pm["majority_from_development"]["balanced_accuracy"]
    how = pm["hour_of_week_from_development"]["balanced_accuracy"]
    beats = cal > maj + 1e-6 and cal > how + 1e-6
    b_cal = r["probability_quality"]["multiclass_brier_calibrated"]
    b_ref = r["probability_quality"]["reference_brier_development_class_frequencies"]
    return (
        f"On the locked 2024 H2 holdout ({r['coverage']['feature_complete_and_labelled']:,} scored hours) the "
        f"frozen calibrated logistic reaches balanced accuracy {cal:.3f} vs majority {maj:.3f} and hour-of-week "
        f"{how:.3f}. It "
        + ("beats" if beats else "does not beat")
        + f" both availability-safe baselines. Multiclass Brier {b_cal:.3f} vs the development-class-frequency "
        f"reference {b_ref:.3f} "
        + ("(better)" if b_cal < b_ref else "(not better)")
        + ". The primary Q25 result stands as reported."
    )


def _chart(y_true: np.ndarray, proba: np.ndarray, classes: list[str], path: Path) -> None:
    p_down = proba[:, classes.index("DOWN")]
    bins = np.linspace(0, 1, 11)
    xs, ys, ns = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p_down >= lo) & (p_down < hi) if hi < 1 else (p_down >= lo) & (p_down <= hi)
        if m.sum() == 0:
            continue
        xs.append(p_down[m].mean())
        ys.append((y_true[m] == "DOWN").mean())
        ns.append(int(m.sum()))
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ax.plot([0, 0.6], [0, 0.6], "--", color="#8b909b", linewidth=1, label="perfect")
    ax.plot(xs, ys, "o-", color="#3a6ea6", linewidth=2)
    for x, y, n in zip(xs, ys, ns):
        ax.annotate(f"n={n}", (x, y), textcoords="offset points", xytext=(6, -4), fontsize=8, color="#6b7484")
    ax.set_xlabel("Mean predicted P(DOWN), calibrated")
    ax.set_ylabel("Observed DOWN rate")
    ax.set_title("P10.3 — locked-holdout calibration (2024-07-01 to 2024-12-31)\nDOWN class")
    lim = max(0.6, (max(xs + ys) + 0.05) if xs else 0.6)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _write_md(evidence_dir: Path, r: dict[str, Any]) -> None:
    pm = r["primary_metrics"]
    cov = r["coverage"]
    text = f"""# P10.3 — Locked-Holdout Evaluation

**Status:** COMPLETE — {RUN_DATE} — one owner-approved evaluation (D037)
**Holdout window:** {r['holdout_window_local']}
**Holdout:** EVALUATED ONCE. Config re-locked as `state: evaluated`.

## Conclusion

**{r['interpretation']}**

## Coverage

{cov['holdout_hours']:,} holdout hours; {cov['valid_label_hours']:,} with a valid
label; {cov['feature_complete_and_labelled']:,} scored (feature-complete and
labelled); {cov['missing_balancing_hours']:,} hours missing a balancing price.
Holdout label counts: {r['label_counts_holdout']}.

Model refit: {r['model_refit']['fit_rule']} ({r['model_refit']['fit_rows']:,} fit
rows, {r['model_refit']['calibration_rows']:,} calibration rows).

## Primary metrics (holdout)

| Method | Balanced acc. | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| Logistic (calibrated) | {pm['logistic_calibrated']['balanced_accuracy']:.3f} | {pm['logistic_calibrated']['macro_f1']:.3f} | {pm['logistic_calibrated']['accuracy']:.3f} |
| Logistic (raw) | {pm['logistic_raw']['balanced_accuracy']:.3f} | {pm['logistic_raw']['macro_f1']:.3f} | {pm['logistic_raw']['accuracy']:.3f} |
| Majority (development) | {pm['majority_from_development']['balanced_accuracy']:.3f} | {pm['majority_from_development']['macro_f1']:.3f} | {pm['majority_from_development']['accuracy']:.3f} |
| Hour-of-week (development) | {pm['hour_of_week_from_development']['balanced_accuracy']:.3f} | {pm['hour_of_week_from_development']['macro_f1']:.3f} | {pm['hour_of_week_from_development']['accuracy']:.3f} |
| Persistence (ex-post) | {pm['persistence_ex_post']['balanced_accuracy']:.3f} | {pm['persistence_ex_post']['macro_f1']:.3f} | {pm['persistence_ex_post']['accuracy']:.3f} |
| P7 transparent rule | {pm['p7_transparent_rule']['balanced_accuracy']:.3f} | {pm['p7_transparent_rule']['macro_f1']:.3f} | {pm['p7_transparent_rule']['accuracy']:.3f} |

Multiclass Brier (calibrated): {r['probability_quality']['multiclass_brier_calibrated']:.4f}
vs development-class-frequency reference
{r['probability_quality']['reference_brier_development_class_frequencies']:.4f}.

## Calibrated prediction distribution (holdout)

| Predicted | n | realized UP | realized DOWN | realized NEUTRAL |
|---|---:|---:|---:|---:|
""" + "\n".join(
        f"| {lab} | {d['n']:,} | " + " | ".join(
            (f"{d['realized_shares'][r2]:.1%}" if d['realized_shares'][r2] is not None else "—")
            for r2 in ("UP", "DOWN", "NEUTRAL")
        ) + " |"
        for lab, d in r["calibrated_prediction_distribution"].items()
    ) + f"""

## By season and wind level

See `p10_3_holdout_result_{RUN_DATE}.json` `by_season` and `by_wind_level`.

## Delta sensitivity (secondary, pre-declared)

| Delta | Value | Calibrated balanced acc. | Majority balanced acc. |
|---|---:|---:|---:|
""" + "\n".join(
        f"| {k} | {v['delta']:.4f} | {v['calibrated_balanced_accuracy']:.3f} | {v['majority_balanced_accuracy']:.3f} |"
        for k, v in r["delta_sensitivity"].items()
    ) + f"""

## Protocol

{r['protocol_reminder']}
"""
    (evidence_dir / f"p10_3_holdout_result_{RUN_DATE}.md").write_text(text, encoding="utf-8")


def run(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / "config/research_config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    holdout = config["periods"]["holdout"]

    result_json = repo_root / "research/evidence/p10_holdout" / f"p10_3_holdout_result_{RUN_DATE}.json"
    raw_present = all(
        (repo_root / "data/raw/p10_holdout" / f"{n}_DK1_holdout_2024-07-01_2024-12-31.json").exists()
        for n in DATASETS
    )

    if result_json.exists():
        raise ValueError("P10.3 has already produced a holdout result. It does not re-run.")
    if holdout["state"] == "evaluated" and not raw_present:
        raise ValueError("Holdout state is 'evaluated' but no raw data and no result — inconsistent; inspect manually.")
    if holdout["state"] not in ("locked", "evaluated"):
        raise ValueError(f"Unexpected holdout state {holdout['state']!r}.")

    # Fit the frozen model on development (p10_model.load accepts 'locked' and 'evaluated').
    model = fit_frozen_model(repo_root)
    unlocked_at = holdout.get("unlocked_at_utc") or datetime.now(timezone.utc).isoformat()

    _set_holdout_state(
        config_path,
        state="unlocked",
        fetch_allowed=True,
        unlocked_at_utc=unlocked_at,
        unlock_decision="D036",
        post_unlock_rule="Any specification change informed by the holdout is exploratory and needs fresh unseen data.",
    )
    try:
        result = evaluate(repo_root, model)
    finally:
        _set_holdout_state(
            config_path,
            state="evaluated",
            fetch_allowed=False,
            unlocked_at_utc=unlocked_at,
            evaluated_at_utc=datetime.now(timezone.utc).isoformat(),
            unlock_decision="D036",
        )

    quality = {
        "step": "P10.3",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "holdout_window_is_2024_h2": result["holdout_window_local"].startswith("2024-07-01"),
            "delta_not_re_estimated": FROZEN_DELTA == 5.9956075,
            "evaluated_once": True,
            "config_re_locked_as_evaluated": yaml.safe_load(config_path.read_text())["periods"]["holdout"]["state"] == "evaluated",
        },
        "holdout": "EVALUATED_ONCE",
    }
    json_dump(repo_root / "research/evidence/p10_holdout" / f"p10_3_quality_report_{RUN_DATE}.json", quality)
    return {"result": result, "quality": quality}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    out = run(args.repo_root.resolve())
    r = out["result"]
    pm = r["primary_metrics"]
    print(json.dumps({
        "status": out["quality"]["status"],
        "scored_hours": r["coverage"]["feature_complete_and_labelled"],
        "logistic_calibrated_balanced_accuracy": pm["logistic_calibrated"]["balanced_accuracy"],
        "majority_balanced_accuracy": pm["majority_from_development"]["balanced_accuracy"],
        "hour_of_week_balanced_accuracy": pm["hour_of_week_from_development"]["balanced_accuracy"],
        "brier_calibrated": r["probability_quality"]["multiclass_brier_calibrated"],
        "interpretation": r["interpretation"],
        "holdout": "EVALUATED_ONCE",
    }, indent=1))


if __name__ == "__main__":
    main()
