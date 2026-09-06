# P10.3 — Locked-Holdout Evaluation Evidence

**Status:** COMPLETE — 2026-09-06 — one owner-approved evaluation (D037)
**Holdout:** EVALUATED ONCE. `config` `state: evaluated`, `fetch_allowed: false`.
The holdout is closed and must not be used again.

`src/p10_holdout_eval.py` fit the frozen P10.1 specification on development data
before 2024-01-01 (16,883 rows), calibrated it (Platt) on the 2024 H1 development
slice (4,207 rows), fetched DK1 `2024-07-01 .. 2024-12-31` for `Forecasts_Hour`,
`Elspotprices`, `RegulatingBalancePowerdata` and `ProductionConsumptionSettlement`,
built the holdout feature table with the frozen delta and thresholds, evaluated
once, and re-locked the config. Raw files are git-ignored under
`data/raw/p10_holdout/`; SHA-256 in `holdout_raw_provenance_2026-09-06.json`.
Tests: `tests/test_p10_holdout_eval.py`. Quality gate:
`p10_3_quality_report_2026-09-06.json`.

## Result — a small out-of-sample edge, not a deployable one

Holdout: 4,417 hours, 4,331 scored (feature-complete and labelled); label mix
UP 645 / DOWN 1,170 / NEUTRAL 2,602.

| Method | Balanced acc. | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| Logistic (calibrated) | **0.352** | **0.297** | 0.593 |
| Logistic (raw) | 0.383 | 0.289 | 0.280 |
| Majority (development) | 0.333 | 0.247 | 0.590 |
| Hour-of-week (development) | 0.329 | 0.280 | 0.553 |
| Persistence (ex-post) | 0.635 | 0.635 | 0.699 |
| P7 transparent rule | 0.348 | 0.349 | 0.471 |

- The calibrated model **beats both availability-safe baselines** on balanced
  accuracy and macro-F1 by ~2 points — real, but within sampling range on 4,331
  hours.
- It predicts `NEUTRAL` for 95% of hours. On the 212 `DOWN` calls the hour is
  `DOWN` 49% of the time vs a 27% base rate — the signal is `DOWN`-side only.
- **No probability skill:** multiclass Brier 0.593 vs the development-class-
  frequency reference 0.582. See `p10_3_holdout_calibration_2026-09-06.png`.
- By season: summer strongest (balanced accuracy 0.362), below majority in winter
  (0.326) — consistent with P4.4. By wind level: all terciles edge majority by
  ~1-2 points.
- Delta sensitivity (pre-declared secondary): Q20 0.355, Q25 (primary) 0.352,
  Q30 0.349 — the primary Q25 specification stands.

**The H2 wind-revision mechanism attenuated but did not vanish out of sample. It
is not an edge worth acting on.** Decision D037. Any follow-up needs fresh, later
data.
