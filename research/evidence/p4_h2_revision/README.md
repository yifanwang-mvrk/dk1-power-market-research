# P4 H2 Renewable Forecast Revision Evidence

**Status:** P4.1 pre-registration recorded 2026-09-06; testing not started
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

What P4.2 adds: the development-derived numbers only (bucket edges, group sizes,
coverage, the `5h == 1h` diagnostic, the normalization floor). The procedure does
not change.

## Next steps

| Step | Action |
|---|---|
| P4.2 | Build wind and solar 5h-to-1h revisions on the P2 base; report the `5h == 1h` and coverage diagnostics; freeze the bucket edges |
| P4.3 | Run the pre-registered round-1 test and produce the chart |
| P4.4 | First-round conditioning and failure analysis |
