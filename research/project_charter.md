# Project Charter

**Project:** DK1 Short-Term Power Market Research
**Version:** MVP v1
**Status:** Frozen design; P3 target construction complete; P4 H2 testing next
**Owner:** Yifan Wang

## Mission

Transform point-in-time DK1 market information into explicit hypotheses, probabilistic directional views and risk-aware research decisions.

## Research Question

> Do renewable forecast revisions and observable system fundamentals contain information about short-term balancing pressure in DK1, and under what conditions does that relationship break down?

## Primary Outcome

For each hourly DK1 delivery period:

`Spread_t = P_Balancing,t - P_DayAhead,t`

P1.2 fixed `P_DayAhead,t` as DK1 `Elspotprices.SpotPriceEUR` in EUR/MWh.
P1.3 fixed `P_Balancing,t` as DK1
`RegulatingBalancePowerdata.ImbalancePriceEUR` in EUR/MWh, subject to one
documented missing development hour. It is an ex-post outcome and not an
executable trading price.

The outcome classes are:

- UP when `Spread_t > delta`
- DOWN when `Spread_t < -delta`
- NEUTRAL when `abs(Spread_t) <= delta`

The frozen numerical value is `delta = 5.9956075 EUR/MWh`, calculated with
linear interpolation as the Q25 of 15,392 nonzero absolute development spreads.
It is fixed before holdout access.

## Hypotheses

- H1: Residual load and system tightness may affect balancing pressure.
- H2: Renewable forecast revisions may contain information about balancing pressure.
- H3: Cross-border and system conditions may change these relationships.

H2 is the primary MVP hypothesis.

## Research Periods

- Development period: 2022-01-01 to 2024-06-30
- Locked holdout: 2024-07-01 to 2024-12-31

The holdout must not be requested, fetched, inspected or analyzed before the Level C unlock requirements are satisfied.

## Point-in-Time Policy

Every field must be assigned to one of three classes:

- `decision_eligible`: available at the simulated decision time
- `diagnostic_only`: useful for explanation but unavailable for the decision
- `outcome`: known only after delivery

Historical availability in an API does not automatically make a field decision eligible.

P2.3 fixes the simulated decision anchor at `delivery_start_utc` and requires
eligible information to be available strictly before it. This is the last
pre-delivery information snapshot and does not imply executable intraday P&L.

## Mandatory Baselines

Every directional result must be compared with:

- Majority-class baseline
- Persistence baseline, retained as an ex-post reference because historical
  outcome publication delay is undocumented

An availability-safe hour-of-week training-majority reference is also
registered and must be fit only within each future training segment.

If the proposed method cannot outperform a valid baseline, the conclusion must state that no useful signal was found.

## Scope Boundaries

The MVP does not claim:

- Executable intraday trading P&L
- A profitable trading strategy
- Causal effects
- Complete tick-by-tick forecast history
- Coverage beyond DK1

## Completion Principle

A hypothesis is complete only after one full test and a written conclusion. A null or failed result still counts as a valid research conclusion.

## Working Principles

- Preserve the frozen target and holdout rules.
- Use only information available at the simulated decision time.
- Keep development and holdout data separate.
- Explain the market mechanism before adding model complexity.
- Record missing data and limitations explicitly.
- Preserve failed and null hypotheses.
- Treat No Trade as a valid decision.
- Compare results with simple baselines.
- Do not rewrite earlier decisions after seeing outcomes.
- Keep public claims aligned with completed evidence.
