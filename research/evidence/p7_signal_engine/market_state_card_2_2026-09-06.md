# DK1 Market State Card 2 (hit)

**Retrospective worked example on development data.** The decision fields are what
the P7 rule would have produced from decision-eligible inputs; the outcome is the
realized label. Not a live card and not executable P&L (D016).

- Card ID: P7-DEV-02
- Delivery hour (UTC): 2022-10-21 09:00:00+00:00
- Delivery hour (local): 2022-10-21 11:00:00+02:00
- Decision cutoff (UTC): 2022-10-21 09:00:00+00:00  (last pre-delivery snapshot, D025)
- Data version: P3 target + P4.2 revision, git-tracked evidence

## Information snapshot (decision-eligible only)

- Day-ahead price (EUR/MWh): 178
- Wind revision 5h->1h (MWh): -86.04
- 5h wind forecast (MWh): 595.2  (in the low-wind blind spot)
- Known residual load proxy (MWh): 2239
- H2 view: none   H1 view: UP

## Market view

- Directional view: UP PRESSURE
- Confidence: LOW
- Primary driver: very tight known residual load; H2 not on the DOWN side
- Counterargument: the underlying H2 association is weak (Spearman ~ -0.10) and did not reproduce on the 2024 H1 hold-back; H1 is threshold-like and weak
- Key risk: realized conditions (outages, demand, cross-border) dominate the hourly balancing outcome
- Invalidation: a low 5h wind forecast (H2 blind spot); renewables arriving far from forecast; the system turning tight against a DOWN view

## Decision

- Decision: Bullish (up pressure)
- No-Trade condition: conflicting H1/H2 views, both views silent, or a missing eligible input

## Outcome (known — retrospective)

- Actual balancing price (EUR/MWh): 336.1
- Actual spread (EUR/MWh): 158.1
- Realized label: UP
- Directionally correct: True

## Post-mortem

- The rule caught the realized direction.
- What was missing: no decision-eligible measure of demand shocks, outages or realized cross-border flow.
- What changes next: a probabilistic model (P10) and, if it becomes available, the ENTSO-E load forecast (I06).
