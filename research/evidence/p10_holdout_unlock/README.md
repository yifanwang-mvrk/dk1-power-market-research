# P10.2 — Holdout Unlock Record

**Status:** complete 2026-09-06 — spec frozen, prior non-use verified
**Holdout:** LOCKED AND UNREAD. `config` keeps `fetch_allowed: false`.
**This step does NOT unlock the holdout.**

`src/p10_unlock_gate.py` freezes the Level C specification and verifies that the
locked holdout (2024-07-01 to 2024-12-31) has never been requested, fetched or
inspected. Files: `unlock_record_2026-09-06.json`, `quality_report_2026-09-06.json`
(6/6). The completed unlock template is in
`docs/decision_log.md` (D036, "Level C 解锁记录模板").

## Prior-non-use verification

- `config` holdout `state: locked`, `fetch_allowed: false`.
- All 6 raw JSON files max at 2024-06-30 (CountertradeIntraday at 2024-06-28);
  SHA-256 recorded.
- All 9 processed parquet tables max at 2024-06-30 21:00:00Z.
- Every data loader aborts unless the holdout is locked and filters strictly
  before the holdout start.
- The only holdout-window dates in the repo are the exclusive request boundary
  2024-07-01, the declared end 2024-12-31, and 2024-11-01/07 inside a third-party
  documentation URL in P1.4 source metadata.

## Frozen specification (from P10.1, commit 47577b1)

- Target: `Spread = ImbalancePriceEUR − SpotPriceEUR` (EUR/MWh); `delta =
  5.9956075` (frozen, not re-estimated); UP / DOWN / NEUTRAL labels.
- Model: multinomial LogisticRegression, `class_weight=balanced`, `C=1.0`;
  StandardScaler on train only; Platt calibration on the calibration slice only.
- 10 decision-eligible features; decision cutoff `delivery_start_utc`.
- Time-ordered development split: train `< 2023-07-01`, calibration `< 2024-01-01`,
  validation `< 2024-07-01`.

## What P10.3 will do (owner-approved only)

1. Log the unlock date/time in D036; set `config` `holdout.fetch_allowed: true`.
2. Request `local 2024-07-01 00:00 .. 2025-01-01 00:00` (exclusive), DK1, through
   the same P2 → P3 → P4.2 pipeline.
3. Evaluate the frozen calibrated model vs majority and hour-of-week (fit on all
   development), with the raw logistic and the P7 rule for comparison and
   persistence as an ex-post reference; report balanced accuracy, macro-F1 and
   multiclass Brier, plus by-season and by-wind-level performance and the
   Q20/Q30 delta sensitivity.
4. Write results to `research/evidence/p10_holdout/`.

**Owner approval: PENDING.**
