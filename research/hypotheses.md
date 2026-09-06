# Hypothesis Registry

**Project:** DK1 Short-Term Power Market Research
**Status:** Pre-registered; testing not started
**Last updated:** 2026-09-06

## H1 — Residual Load and System Tightness

**Status:** Source registered; testing not started
**Role:** Fundamental baseline hypothesis

### Question

Does higher residual load increase the probability of upward balancing pressure in DK1?

### Mechanism

Residual load represents demand remaining after wind and solar generation are deducted. Higher residual load may require more flexible conventional supply and may therefore be associated with tighter system conditions.

### Point-in-Time Constraint

Actual demand and actual renewable production may explain past outcomes but cannot be used as decision inputs unless equivalent forecasts were available at the simulated decision time.

P1.4 selected `ProductionConsumptionSettlement` for H1-A. Actual residual load
is gross consumption minus summed actual wind and actual solar. It is
`diagnostic_only` because settlement data arrive after delivery and can be
revised. The full development period contains 21,887 complete derived rows.

No validated historical Energi Data Service load-forecast source was found for
H1-B. The ENTSO-E day-ahead total-load forecast is registered as an external
candidate pending access and publication-timing evidence in P5.2.

## H2 — Renewable Forecast Revision

**Status:** Forecast, day-ahead reference and balancing outcome validated; testing not started
**Role:** Primary MVP hypothesis

### Question

Do renewable forecast revisions contain information about the direction of balancing pressure?

### Candidate Variable

`Forecast Revision = Forecast1Hour - Forecast5Hour`

A positive wind revision means expected wind production increased as delivery approached. All directional relationships must be tested rather than assumed.

### Point-in-Time Constraint

P1.1 established same-hour fixed-horizon fields with approximately 99% numeric
pair coverage in the development period. Use them only with the documented
missingness, zero-value and DST rules. The exact simulated decision cutoff
remains to be locked in P2.3; no complete tick-by-tick vintage claim is allowed.
P1.2 fixed the same-hour DK1 day-ahead reference as
`Elspotprices.SpotPriceEUR` in EUR/MWh with complete development-period
coverage. P1.3 fixed the ex-post balancing outcome as
`RegulatingBalancePowerdata.ImbalancePriceEUR` in EUR/MWh. Its official
development extract is missing one complete DST fall-back hour, which must
remain missing rather than be filled with zero.

## H3 — Cross-Border and System Conditions

**Status:** Sources registered; testing not started
**Role:** Conditional hypothesis

### Question

Do cross-border conditions change the relationship between renewable forecast revisions and balancing pressure?

### Mechanism

Available transmission capacity, scheduled exchange and neighboring-market conditions may absorb or amplify local DK1 imbalances.

### Point-in-Time Constraint

Each cross-border field must be classified as decision eligible, diagnostic only or unavailable before use.

P1.4 registered `Transmissionlines.ImportCapacity`, `ExportCapacity` and
`ScheduledExchangeDayAhead` as conditional decision candidates. P2.3 must map
them to the exact decision cutoff, and P6.1 must handle border-specific
coverage, nulls and mixed export-capacity signs. Final intraday schedules and
physical settlement flows are diagnostic only.

Legacy `CountertradeIntraday` is a partial-period conditional candidate from
2023-04-18. Later versions overwrite earlier history, so P2.3 must accept only
rows available at the cutoff and must not infer that absent publication days
mean zero. The 2025 successor is unavailable for development.

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
