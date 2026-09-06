# P4 H2 Renewable Forecast Revision Evidence

**Status:** P4.1 pre-registration and P4.2 revision build complete 2026-09-06;
round-1 test (P4.3) not started
**Holdout:** LOCKED AND UNUSED

## P4.1 — Pre-registered test specification

`p4_1_preregistration_2026-09-06.json` is the frozen snapshot of the H2 round-1
test, registered before any revision variable was constructed and before any
revision-outcome relationship was inspected on development data. The readable
version lives in `research/hypotheses.md` under "H2 — Renewable Forecast
Revision / P4.1 Pre-Registered Test Specification".

What is fixed in advance:

- Revision variable: `Forecast1Hour - Forecast5Hour` per forecast type, same
  `HourUTC + PriceArea + ForecastType` row, both horizons non-null (D021); wind
  aggregated across offshore and onshore.
- Primary test: `wind_revision_t` in raw MWh — this alone decides whether H2 is
  supported. Solar runs the identical procedure as a separate secondary test; a
  solar-only pass is "conditionally supported - solar only, needs replication".
- Expected direction: positive wind revision favours `DOWN`, negative favours
  `UP`; contrary and null outcomes are admissible and must be reported.
- Buckets: five ordered groups by development-only signed quantiles
  Q20 / Q40 / Q60 / Q80 (primary), plus a ten-decile secondary view. Edges
  computed and frozen in P4.2.
- Method: bucket-by-label contingency table; Spearman association (primary vs the
  continuous signed spread, secondary vs the `+1/0/-1` label score) with a
  bootstrap CI; one transparent rule with `c` fixed at the development Q60
  magnitude; one chart.
- Baselines: majority, hour-of-week training majority and persistence are all
  reported. The rule's pass/fail is judged only against the two availability-safe
  baselines (majority and hour-of-week); persistence is an ex-post reference
  (D023, E001), reported prominently but not a gate.
- Success requires the directional gradient, a non-zero signed association, and
  the rule beating both availability-safe baselines on balanced accuracy and
  macro-F1. Otherwise the result is conditionally supported (mechanism only) or
  rejected / null, and is retained in full.

## P4.2 — Revision build and diagnostics

`src/p4_revision.py` builds the revisions on the frozen P2 hourly base, joins no
outcome, and writes `p4_2_revision_build_2026-09-06.json`,
`p4_2_bucket_freeze_2026-09-06.json`, `p4_2_diagnostics_2026-09-06.md`,
`revision_audit_sample_2026-09-06.csv` and `quality_report_2026-09-06.json`
(12/12 critical checks). Local table: `data/processed/p4/revision_development.parquet`.

Headline results:

- Wind aggregate revision available for 21,615 of 21,887 development hours
  (98.8%); 272 dropped for a missing horizon (D021, never zero-filled).
- The wind forecast moves in essentially every hour: `Forecast5Hour ==
  Forecast1Hour` exactly in 0 wind-aggregate hours; only 0.6% of hours have
  `abs(wind_revision) <= 1 MWh`. The revision variable carries real information.
- Solar has `5h == 1h` exactly in 4,676 hours (21.6%, night 0 -> 0); the solar
  secondary test uses the both-horizons-positive subset (14,837 hours).
- Frozen signed `wind_revision` quintile edges (MWh): -101.100 / -27.250 /
  +42.125 / +163.683, five equal groups of 4,323.
- Frozen transparent-rule threshold `c` = Q60 of `abs(wind_revision)` =
  128.083 MWh. Normalization floor for `wind_forecast_5h` = 276.575 MWh.
- Output table carries no outcome column; no revision-outcome statistic computed.

## Next steps

| Step | Action |
|---|---|
| P4.3 | Join the frozen revisions to the P3 labels/spread; run the pre-registered contingency table, Spearman association and transparent rule; produce the chart |
| P4.4 | First-round conditioning and failure analysis |
