# DK1 Short-Term Power Market Research

Independent, point-in-time research into whether renewable forecast revisions and observable system conditions contain information about short-term balancing pressure in DK1.

## Current Status

Project foundation, official-source validation and the development data
pipeline are complete. Target construction is next.

- Repository structure and GitHub remote: created
- Python environment: created and verified
- Data validation: P1 complete; source roles and point-in-time eligibility inventoried
- Data pipeline: P2 complete; bounded acquisition, raw provenance, timestamp
  normalization, hourly joins and quality gates passed
- Hypothesis testing: not started
- Level A (CV-safe): not achieved
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

## Research Principles

- Use only information available at the simulated decision time.
- Keep the development period separate from the locked holdout.
- Test market mechanisms before increasing model complexity.
- Preserve failed and null hypotheses.
- Treat No Trade as a valid decision.
- Do not present balancing-pressure classification as executable trading P&L.
