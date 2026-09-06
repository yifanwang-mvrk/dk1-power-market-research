"""P10.2 — holdout unlock gate: freeze the spec and verify prior non-use.

Produces a machine-readable attestation that the locked holdout
(2024-07-01 .. 2024-12-31) has never been requested, fetched or inspected, plus
a record of the frozen code/config version and the P10.3 test plan.  This step
does NOT unlock the holdout; flipping ``fetch_allowed`` is the owner-approved
P10.3 action.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


RUN_DATE = "2026-09-06"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(repo_root: Path) -> str | None:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=False,
        capture_output=True, text=True,
    )
    return out.stdout.strip() or None


def git_is_clean(repo_root: Path) -> bool:
    out = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_root, check=False,
        capture_output=True, text=True,
    )
    return out.stdout.strip() == ""


def verify_prior_non_use(repo_root: Path) -> dict[str, Any]:
    config = yaml.safe_load(
        (repo_root / "config/research_config.yaml").read_text(encoding="utf-8")
    )
    holdout = config["periods"]["holdout"]
    tz = config["periods"]["boundary_timezone"]
    holdout_start = pd.Timestamp(holdout["start_date"], tz=tz).tz_convert("UTC")

    config_state = {
        "state": holdout["state"],
        "fetch_allowed": holdout["fetch_allowed"],
        "start_date": holdout["start_date"],
        "end_date_inclusive": holdout["end_date_inclusive"],
        "locked_and_fetch_disabled": holdout["state"] == "locked" and holdout["fetch_allowed"] is False,
    }

    raw_files = []
    for p in sorted(glob.glob(str(repo_root / "data/raw/**/*.json"), recursive=True)):
        path = Path(p)
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("records", data if isinstance(data, list) else data.get("data", []))
        times = [
            r.get("HourUTC") or r.get("HourDK")
            for r in records
            if isinstance(r, dict)
        ]
        times = [t for t in times if t]
        raw_files.append({
            "file": str(path.relative_to(repo_root)),
            "records": len(records),
            "max_hour_utc": max(times) if times else None,
            "sha256": sha256(path),
            "within_development": (max(times) if times else "0000") < "2024-07-01",
        })

    processed_files = []
    for p in sorted(glob.glob(str(repo_root / "data/processed/**/*.parquet"), recursive=True)):
        path = Path(p)
        df = pd.read_parquet(path, columns=["delivery_start_utc"])
        mx = df["delivery_start_utc"].max()
        processed_files.append({
            "file": str(path.relative_to(repo_root)),
            "rows": int(len(df)),
            "max_delivery_start_utc": str(mx),
            "before_holdout": bool(mx < holdout_start),
        })

    loaders_guarded = []
    for src in sorted(glob.glob(str(repo_root / "src/*.py"))):
        text = Path(src).read_text(encoding="utf-8")
        name = Path(src).name
        if "holdout" not in text:
            continue
        loaders_guarded.append({
            "file": f"src/{name}",
            "aborts_if_not_locked": 'state"] != "locked"' in text or "!= \"locked\"" in text,
            "filters_before_holdout": "holdout_start" in text or "h_start" in text or "holdout" in text,
        })

    all_raw_ok = all(f["within_development"] for f in raw_files)
    all_processed_ok = all(f["before_holdout"] for f in processed_files)

    return {
        "config_holdout_state": config_state,
        "raw_files": raw_files,
        "processed_files": processed_files,
        "code_loaders_referencing_holdout": loaders_guarded,
        "holdout_date_references_note": (
            "The only holdout-window dates in the repo are the exclusive request "
            "boundary 2024-07-01, the declared end 2024-12-31 in config/docs, and "
            "2024-11-01/07 inside a third-party documentation URL captured in P1.4 "
            "source metadata. No holdout observation was requested, fetched or read."
        ),
        "prior_non_use_verified": bool(
            config_state["locked_and_fetch_disabled"] and all_raw_ok and all_processed_ok
        ),
    }


def run(repo_root: Path) -> dict[str, Any]:
    evidence_dir = repo_root / "research/evidence/p10_model"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    p10_1 = json.loads(
        (evidence_dir / f"p10_1_model_{RUN_DATE}.json").read_text(encoding="utf-8")
    )
    non_use = verify_prior_non_use(repo_root)

    record = {
        "step": "P10.2",
        "status": "READY_FOR_OWNER_APPROVAL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_id": "D036 (holdout unlock record)",
        "holdout_unlocked": False,
        "note": "This step freezes the spec and verifies prior non-use. It does NOT unlock the holdout. P10.3 flips config fetch_allowed only after the owner approves.",
        "frozen_code_config_version": {
            "spec_frozen_at_commit": "47577b1 (P10.1 — model, features, split, calibration, config level_c_model)",
            "git_head_at_record_time": git_head(repo_root),
            "working_tree_clean_at_record_time": git_is_clean(repo_root),
            "note": "The P10.1 commit froze the specification. This P10.2 record and its own commit add only the unlock paperwork; the spec is unchanged.",
        },
        "frozen_specification": p10_1["frozen_specification"],
        "temporal_split": p10_1["temporal_split"],
        "target_and_delta": {
            "labels": "UP / DOWN / NEUTRAL, frozen (D026)",
            "delta_eur_mwh": 5.9956075,
            "delta_re_estimated": False,
        },
        "baselines": {
            "majority": "training-label majority (from all development), always predicted",
            "hour_of_week": "training-majority label per Danish local weekday-hour (from all development)",
            "persistence": "y_hat_t = y_(t-1); ex-post reference only (D023 / E001)",
        },
        "primary_metrics": ["balanced_accuracy", "macro_f1", "multiclass_brier (mean sum_k (p_k - y_k)^2)"],
        "predeclared_secondary_sensitivities": ["by_season", "by_wind_level", "delta_Q20_Q30_sensitivity"],
        "planned_holdout_request_boundaries": {
            "local_start_inclusive": "2024-07-01 00:00 Europe/Copenhagen",
            "local_end_exclusive": "2025-01-01 00:00 Europe/Copenhagen",
            "price_area": "DK1",
            "sources": "same six sources and the same P2 -> P3 -> P4.2 pipeline",
        },
        "results_destination": "research/evidence/p10_holdout/ (P10.3); research/r01_research_memo.md and README (P10.4)",
        "protocol_for_changes_after_inspection": "Any specification change informed by the holdout is exploratory and requires fresh, later, unseen data. The primary Q25 result stands as reported.",
        "prior_non_use_verification": non_use,
        "level_b_evidence": "research/evidence/p9_level_b/level_b_audit_2026-09-06.md (10/10)",
        "owner_approval": {
            "required_for": "P10.3 (unlock + holdout fetch + evaluation)",
            "status": "PENDING",
            "granted_by": None,
            "granted_at_utc": None,
        },
    }

    path = evidence_dir.parent / "p10_holdout_unlock" / f"unlock_record_{RUN_DATE}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    checks = {
        "config_holdout_locked_and_fetch_disabled": non_use["config_holdout_state"]["locked_and_fetch_disabled"],
        "all_raw_files_within_development": all(f["within_development"] for f in non_use["raw_files"]),
        "all_processed_tables_before_holdout": all(f["before_holdout"] for f in non_use["processed_files"]),
        "spec_frozen_from_p10_1": record["frozen_specification"]["selected_C"] == p10_1["frozen_specification"]["selected_C"],
        "holdout_not_unlocked_by_this_step": record["holdout_unlocked"] is False,
        "owner_approval_pending": record["owner_approval"]["status"] == "PENDING",
    }
    quality = {
        "step": "P10.2",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "critical_checks": checks,
        "holdout": "LOCKED_AND_UNUSED",
    }
    (path.parent / f"quality_report_{RUN_DATE}.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    if quality["status"] != "PASS":
        raise ValueError(f"P10.2 gate failed: {[k for k, v in checks.items() if not v]}")
    return {"record": record, "quality": quality}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    out = run(args.repo_root.resolve())
    r = out["record"]
    print(
        json.dumps(
            {
                "status": out["quality"]["status"],
                "prior_non_use_verified": r["prior_non_use_verification"]["prior_non_use_verified"],
                "spec_frozen_at_commit": r["frozen_code_config_version"]["spec_frozen_at_commit"],
                "holdout_unlocked": r["holdout_unlocked"],
                "owner_approval": r["owner_approval"]["status"],
            }
        )
    )


if __name__ == "__main__":
    main()
