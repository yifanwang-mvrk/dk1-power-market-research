# DK1 Short-Term Power Market Research

Independent, point-in-time research into whether renewable forecast revisions and observable system conditions contain information about short-term balancing pressure in DK1.

## Current Status

Project foundation is complete. Official-source validation is in progress.

- Repository structure and GitHub remote: created
- Python environment: created and verified
- Data validation: P1.1 conditionally passed; P1.2 passed; P1.3 conditionally passed; P1.4 current
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

## Research Principles

- Use only information available at the simulated decision time.
- Keep the development period separate from the locked holdout.
- Test market mechanisms before increasing model complexity.
- Preserve failed and null hypotheses.
- Treat No Trade as a valid decision.
- Do not present balancing-pressure classification as executable trading P&L.
