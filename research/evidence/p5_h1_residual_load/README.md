# P5 — H1 Residual Load and System Tightness Evidence

**Status:** P5.1 and P5.2 complete 2026-09-06 — Level B B2 done
**Holdout:** LOCKED AND UNUSED

`src/p5_residual_load.py` builds actual residual load from the P3 settlement
diagnostics (H1-A) and a point-in-time climatology proxy (H1-B), and relates each
to the frozen balancing spread and label. Tests: `tests/test_p5_residual_load.py`.
Quality gate: `p5_quality_report_2026-09-06.json` (7/7).

## P5.1 — H1-A (diagnostic)

`residual_load_actual_mwh = actual_gross_consumption − Σ actual wind − Σ actual
solar`. `diagnostic_only` (D024): settlement data, published ~9–15 days after
delivery and revised; it explains realized conditions and is never a decision
input. Complete for all 21,887 hours; 5,974 negative-value hours preserved.

**Conclusion: directionally present but weak and threshold-like.** `P(DOWN)` sits
near 35% through the lower three residual-load quintiles then falls to 27% in the
tightest quintile; `P(UP)` edges 18% → 23%. Gradient Spearman +0.70 (not smooth);
Spearman(residual load, signed spread) +0.057, 95% CI [+0.043, +0.070] — right
sign, real, small. The "tighter system → upward pressure" mechanism appears only
once the system is actually tight.

**Relation to H2:** the effect concentrates in the wind-poor / tight region where
H2 fails (P4.4). H1 and H2 look complementary; joint use is P7.

Files: `p5_1_h1a_mechanism_2026-09-06.json`,
`p5_1_residual_load_label_chart_2026-09-06.png`.

## P5.2 — H1-B (decision-eligible proxy)

`residual_load_known_mwh = consumption_climatology_mwh − renewable_forecast_5h_mwh`
— a point-in-time expanding same-(weekday, hour) consumption mean, lagged 3
occurrences past the settlement delay, minus the 5h offshore + onshore + solar
forecast. Both inputs available strictly before delivery (D025). Available for
21,184 / 21,887 hours.

- Tracks actual residual load: Spearman +0.92.
- Reproduces the H1 direction (gradient Spearman +0.90; spread association +0.042,
  CI excludes zero) — but that association is as weak as H1-A.

**Registration: `ELIGIBLE_INTERIM_PROXY`** (config
`source_eligibility.residual_load_known_proxy`). An eligible input for the P7
signal engine, not a standalone signal. A stronger H1-B needs the external
ENTSO-E day-ahead total-load forecast (I06, pending access).

Files: `p5_2_h1b_assessment_2026-09-06.json`.

## Next steps

| Step | Action |
|---|---|
| P6 | H3 cross-border conditioning of the H2 gradient (eligible vs diagnostic) |
| P7 | Transparent signal engine combining the H2 wind revision and the H1-B proxy |
