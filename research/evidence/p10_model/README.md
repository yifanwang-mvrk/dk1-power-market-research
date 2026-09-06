# P10 — Level C: Model, Calibration and Holdout Evidence

**Status:** P10.1 complete 2026-09-06 — model and calibration frozen
**Holdout:** LOCKED AND UNREAD. P10.3 (the single holdout evaluation) has not run.

## P10.1 — logistic regression and calibration (development only)

`src/p10_model.py` fits a multinomial `LogisticRegression`
(`class_weight="balanced"`, `C = 1.0` from `[0.05, 0.1, 0.25, 0.5, 1.0]`) on ten
decision-eligible features against the frozen three-class label. Tests:
`tests/test_p10_model.py`. Quality gate: `p10_1_quality_report_2026-09-06.json`
(8/8). Files: `p10_1_model_2026-09-06.{json,md}`,
`p10_1_calibration_chart_2026-09-06.png`.

**Features (decision-eligible):** `wind_revision_mwh`, `wind_forecast_5h_mwh`, a
`wind_revision_when_low_wind_mwh` interaction, `solar_revision_mwh`, the H1-B
`residual_load_known_mwh` proxy, cyclical hour and day-of-year, weekend.

**Time-ordered development split:** train `< 2023-07-01` (12,478), calibration
`[2023-07-01, 2024-01-01)` (4,405), validation `[2024-01-01, 2024-07-01)`
(4,207). Calibration is Platt (sigmoid), fit on the calibration slice only
(lower validation Brier than isotonic). Multiclass Brier convention:
`mean sum_k (p_k - y_k)^2`, range `[0, 2]`.

### Result

- **The coefficient signs match the H1/H2 mechanisms on all five checked terms**
  (positive wind revision → DOWN, more expected wind → DOWN, looser residual load
  → DOWN, and the mirror for UP). The model learned the right directions.
- **No edge on the 2024 H1 validation slice.** Class-weighted argmax balanced
  accuracy 0.354 (vs 0.333 chance, like the P7 rule); the calibrated argmax
  collapses to the majority class (0.333). Calibrated multiclass Brier 0.642 is
  worse than the train-frequency reference 0.637.
- Consistent with P4.4 — 2024 H1 is exactly where the H2 gradient did not
  reproduce. A weak validation-slice result is expected and is itself
  informative.

Decision D035; I08 resolved; config `level_c_model`.

## P10.2 / P10.3 test plan (frozen)

- Freeze this specification and the frozen target.
- Complete the decision-log holdout-unlock template: unlock date, frozen
  code/config version, prior-non-use evidence, planned request boundaries.
- **Holdout request:** local 2024-07-01 00:00 inclusive to 2025-01-01 00:00
  exclusive, DK1, same sources and pipeline.
- **Primary report:** calibrated logistic vs majority and hour-of-week (fit on
  all development) on balanced accuracy, macro-F1 and multiclass Brier;
  persistence as an ex-post reference; the P7 transparent rule and the raw
  (uncalibrated) logistic for comparison.
- **Secondary:** by-season and by-wind-level performance; Q20 / Q30 delta
  sensitivity.
- Any change informed by the holdout is exploratory and needs fresh unseen data.

**P10.3 requires the project owner's explicit approval to unlock the holdout.**
