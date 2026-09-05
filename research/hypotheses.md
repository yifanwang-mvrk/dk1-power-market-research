# Hypothesis Registry

**Project:** DK1 Short-Term Power Market Research
**Status:** Pre-registered; testing not started
**Last updated:** 2026-09-05

## H1 — Residual Load and System Tightness

**Status:** Not started
**Role:** Fundamental baseline hypothesis

### Question

Does higher residual load increase the probability of upward balancing pressure in DK1?

### Mechanism

Residual load represents demand remaining after wind and solar generation are deducted. Higher residual load may require more flexible conventional supply and may therefore be associated with tighter system conditions.

### Point-in-Time Constraint

Actual demand and actual renewable production may explain past outcomes but cannot be used as decision inputs unless equivalent forecasts were available at the simulated decision time.

## H2 — Renewable Forecast Revision

**Status:** Not started
**Role:** Primary MVP hypothesis

### Question

Do renewable forecast revisions contain information about the direction of balancing pressure?

### Candidate Variable

`Forecast Revision = Forecast1Hour - Forecast5Hour`

A positive wind revision means expected wind production increased as delivery approached. All directional relationships must be tested rather than assumed.

### Point-in-Time Constraint

The forecast horizons, publication timing and historical availability must be validated before constructing the revision variable.

## H3 — Cross-Border and System Conditions

**Status:** Not started
**Role:** Conditional hypothesis

### Question

Do cross-border conditions change the relationship between renewable forecast revisions and balancing pressure?

### Mechanism

Available transmission capacity, scheduled exchange and neighboring-market conditions may absorb or amplify local DK1 imbalances.

### Point-in-Time Constraint

Each cross-border field must be classified as decision eligible, diagnostic only or unavailable before use.

## Research Rule

Each hypothesis must retain:

- Original question
- Market mechanism
- Eligible inputs
- Test specification
- Result
- Counterargument
- Invalidation condition
- Final conclusion

A null or failed result remains part of the research record.
