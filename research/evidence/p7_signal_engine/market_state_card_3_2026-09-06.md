# DK1 Market State Card 3 (miss)

**Retrospective worked example on development data.** The decision fields are what
the P7 rule would have produced from decision-eligible inputs; the outcome is the
realized label. Not a live card and not executable P&L (D016).

- Card ID: P7-DEV-03
- Delivery hour (UTC): 2023-09-20 08:00:00+00:00
- Delivery hour (local): 2023-09-20 10:00:00+02:00
- Decision cutoff (UTC): 2023-09-20 08:00:00+00:00  (last pre-delivery snapshot, D025)
- Data version: P3 target + P4.2 revision, git-tracked evidence

## Information snapshot (decision-eligible only)

- Day-ahead price (EUR/MWh): 0.06
- Wind revision 5h->1h (MWh): 358
- 5h wind forecast (MWh): 2771  (wind not low)
- Known residual load proxy (MWh): 60.25
- H2 view: DOWN   H1 view: none

## Market view

- Directional view: DOWN PRESSURE
- Confidence: MEDIUM
- Primary driver: large positive wind revision, wind not low; H1 not tight
- Counterargument: the underlying H2 association is weak (Spearman ~ -0.10) and did not reproduce on the 2024 H1 hold-back; H1 is threshold-like and weak
- Key risk: realized conditions (outages, demand, cross-border) dominate the hourly balancing outcome
- Invalidation: a low 5h wind forecast (H2 blind spot); renewables arriving far from forecast; the system turning tight against a DOWN view

## Decision

- Decision: Bearish (down pressure)
- No-Trade condition: conflicting H1/H2 views, both views silent, or a missing eligible input

## Outcome (known — retrospective)

- Actual balancing price (EUR/MWh): 9
- Actual spread (EUR/MWh): 8.94
- Realized label: UP
- Directionally correct: False

## Post-mortem

- The rule was directionally wrong here — a reminder that the edge is small and noisy.
- What was missing: no decision-eligible measure of demand shocks, outages or realized cross-border flow.
- What changes next: a probabilistic model (P10) and, if it becomes available, the ENTSO-E load forecast (I06).
