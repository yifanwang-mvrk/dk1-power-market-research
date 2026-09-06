# DK1 Short-Term Power Market Research

Independent, point-in-time research into whether renewable forecast revisions and observable system conditions contain information about short-term balancing pressure in DK1.

## Current Status

**Level B (Interview Ready) is achieved.** All three hypotheses have been tested
one full round, a transparent signal engine with confidence and risk framing is
built, and a research memo is written. Level C (the locked-holdout evaluation) is
the last MVP milestone.

- Data foundation: P1–P3 complete — validated official sources, a point-in-time
  hourly pipeline (21,887 development hours), a frozen three-class target
  (`δ = 5.9956075 EUR/MWh`)
- **H2** renewable forecast revision (primary): pre-registered, then tested and
  conditioned — **conditionally supported** (real by permutation, weak,
  DOWN-side only, fails at low wind, unproven out of time)
- **H1** residual load: weak, threshold-like, diagnostic; a decision-eligible
  proxy is registered
- **H3** cross-border: diagnostic conditioning only — no decision-eligible signal
- **Signal engine:** a transparent rule → UP PRESSURE / DOWN PRESSURE / NO TRADE
  with confidence and invalidation; active in 33% of hours, a modest DOWN-side edge
- Research memo: [`research/r01_research_memo.md`](research/r01_research_memo.md)
- Level A audited (P8.1), Level B audited (P9.2); Level C not started
- Locked holdout: unused

## Research Question

> Do renewable forecast revisions and observable system fundamentals contain information about short-term balancing pressure in DK1, and under what conditions does that relationship break down?

## Primary Target

For each hourly DK1 delivery period:

`Spread_t = RegulatingBalancePowerdata.ImbalancePriceEUR_t - Elspotprices.SpotPriceEUR_t`

The DK1 day-ahead reference is fixed as `SpotPriceEUR` and the historical
balancing outcome as `ImbalancePriceEUR`, both in EUR/MWh. The balancing source
has one documented missing development hour and is used as an ex-post research
outcome rather than an executable trading price.

The frozen development-only neutral-band threshold is `5.9956075 EUR/MWh`.
Valid target labels are `UP` above `+delta`, `DOWN` below `-delta`, and
`NEUTRAL` on both boundaries and between them.

## Research Periods

- Development period: 2022-01-01 to 2024-06-30
- Locked holdout: 2024-07-01 to 2024-12-31

The holdout must not be accessed before the Level C unlock requirements are satisfied.

## Validated Source Roles

- Renewable fixed-horizon forecasts: `Forecasts_Hour`, conditionally eligible
  subject to the P2.3 decision-cutoff contract
- Day-ahead reference: `Elspotprices.SpotPriceEUR`, validated across all
  21,887 development hours
- Balancing outcome: `RegulatingBalancePowerdata.ImbalancePriceEUR`, with one
  documented missing development hour preserved
- Actual residual load and realized exchange:
  `ProductionConsumptionSettlement`, complete but diagnostic only because it
  is settlement data published after delivery
- Day-ahead cross-border capacity and schedule: `Transmissionlines`,
  conditional candidates with border-specific null/sign rules still required
- Countertrade: partial-period conditional candidate; historical versions are
  not fully reconstructable
- H1-B historical load forecast: external ENTSO-E candidate pending access and
  timing evidence

The P1.4 evidence, raw-file hashes and machine-readable eligibility inventory
are preserved in [`research/evidence/p1_4_sources`](research/evidence/p1_4_sources/README.md).

## Development Data Pipeline

P2 produces a local, git-ignored hourly development table at
`data/processed/p2/hourly_base_development.parquet`. It contains 21,887 unique
DK1 delivery hours and preserves the documented single balancing-source gap.
The committed audit evidence is under
[`research/evidence/p2_data_pipeline`](research/evidence/p2_data_pipeline/README.md).

- The API client rejects dates outside development and rejects non-DK1 requests
  before contacting the source.
- Raw JSON responses remain immutable; request details, retrieval times and
  SHA-256 hashes provide provenance.
- UTC is the join key; Danish local time, UTC offset and repeated-hour order are
  retained for DST interpretation.
- The decision cutoff is the last information snapshot before delivery starts.
  Fixed 5h/1h forecasts qualify under the official pre-delivery availability
  rule, while outcomes and settlement actuals remain quarantined.
- P2 does not calculate spread, labels or forecast revisions. Those begin in P3
  and P4.

Rebuild the local P2 outputs with:

```bash
uv run python src/p2_pipeline.py
```

## Target Construction

P3 produces a local, git-ignored target table at
`data/processed/p3/target_development.parquet`. It retains all 21,887 P2 hours,
adds the same-hour balancing spread and assigns 21,886 valid labels while
preserving the documented missing balancing outcome as a missing target.
Committed evidence is under
[`research/evidence/p3_target_construction`](research/evidence/p3_target_construction/README.md).

- `Spread = ImbalancePriceEUR - SpotPriceEUR`, using DK1 EUR/MWh prices for the
  same delivery hour
- `delta = 5.9956075 EUR/MWh`, the linear Q25 of 15,392 nonzero absolute
  development spreads; 6,494 observed zero spreads are excluded from the
  quantile population and later labelled NEUTRAL
- Development labels: 4,354 UP, 7,190 DOWN and 10,342 NEUTRAL, plus one missing
  label at the preserved source gap
- The majority baseline is fit on training labels only. The frozen persistence
  formula is retained as an ex-post reference because historical publication
  delay is undocumented.
- An hour-of-week training-majority baseline is registered as an
  availability-safe supplemental reference for later chronological evaluation.

Rebuild and validate the local P3 target with:

```bash
uv run python src/p3_target.py
```

## H2 — First Hypothesis Test

The primary hypothesis (H2) asks whether the 5h-to-1h renewable forecast
revision carries information about the direction of balancing pressure. The
round-1 test was **pre-registered in full** — variable, expected direction,
buckets, statistic, baselines and the pass/fail bar were fixed before the
revision variable was crossed with any outcome
([`research/hypotheses.md`](research/hypotheses.md),
[evidence](research/evidence/p4_h2_revision/README.md)).

- **Revision variable (P4.2):** `wind_revision = (Offshore + Onshore)
  (Forecast1Hour - Forecast5Hour)`, MWh, same delivery hour, non-null pairs
  only. Available for 21,615 of 21,887 development hours. The wind forecast is
  revised in essentially every hour, so the variable carries real information.
- **Result (P4.3), in-sample / descriptive:** **supported, but a weak and
  asymmetric effect.** As the wind revision goes from most negative to most
  positive, `P(DOWN)` rises from 27.3% to 38.7% and `P(UP)` falls from 24.7% to
  17.2%, monotonically across all five revision quintiles — the predicted
  mechanism. The rank association is real but small (Spearman -0.10, 95%
  bootstrap CI [-0.11, -0.08]). A transparent threshold rule beats the
  availability-safe baselines on balanced accuracy and macro-F1 but not on plain
  accuracy, and trails the ex-post persistence reference; its directional skill
  is real on the `DOWN` side and essentially absent on the `UP` side.
- **Solar** revisions show the same direction, weaker, and are reported
  separately as "conditionally supported — solar only, needs replication".
- **Conditioning (P4.4):** a permutation null confirms the edge is real (not
  chance); it holds across season and hour-of-day; it **fails at low expected
  wind**; and it did **not reproduce** on a 2024 H1 chronological hold-back.
- **H1 and H2 are complementary.** H1 (residual load) is weak and threshold-like
  but picks up exactly in the tight, wind-poor hours where H2 fails.
- This is not a deployable or profitable rule. The locked-holdout evaluation
  (Level C) is the real out-of-sample test.

![Balancing-pressure label share by wind-revision quintile](research/evidence/p4_h2_revision/p4_3_revision_label_chart_2026-09-06.png)

Reproduce the full hypothesis and signal chain with:

```bash
uv run python src/p4_revision.py       # build revisions, freeze buckets
uv run python src/p4_test.py           # pre-registered H2 round-1 test
uv run python src/p4_conditioning.py   # H2 regime / time / permutation stress tests
uv run python src/p5_residual_load.py  # H1-A mechanism + H1-B proxy
uv run python src/p6_cross_border.py   # H3 cross-border conditioning
uv run python src/p7_signal_engine.py  # transparent signal, cards, journal
```

## Research Principles

- Use only information available at the simulated decision time.
- Keep the development period separate from the locked holdout.
- Test market mechanisms before increasing model complexity.
- Preserve failed and null hypotheses.
- Treat No Trade as a valid decision.
- Do not present balancing-pressure classification as executable trading P&L.
