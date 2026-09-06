# Market Journal

**Project:** DK1 Short-Term Power Market Research
**Status:** First research-round entry recorded (J001)

## Entry Template

### Identification

- Journal ID:
- Created at:
- Delivery hour:
- Decision cutoff:
- Data version:

### Information Snapshot

- Day-ahead price:
- Renewable forecast revision:
- Residual-load condition:
- Cross-border condition:
- Other relevant information:

### Market View

- Directional view: Bullish / Bearish / No Trade
- Expected outcome class: UP / DOWN / NEUTRAL
- Probability:
- Confidence: Low / Medium / High
- Main driver:
- Counterargument:
- Key risk:

### Decision

- Decision:
- Reason:
- No-Trade condition:
- Invalidation condition:

### Outcome

Complete only after the delivery result is available.

- Actual day-ahead price:
- Actual balancing price:
- Actual spread:
- Actual outcome class:
- Directionally correct:
- Baseline result:

### Post-Mortem

- What was correct:
- What was wrong:
- What information was missing:
- Was the original reasoning valid:
- What should change:


---

## Entry J001 — H2/H1/H3 first research round (retrospective)

### Identification

- Journal ID: J001
- Created at: 2026-09-06
- Delivery hour: development period 2022-01-01 to 2024-06-30 (aggregate)
- Decision cutoff: delivery-hour start, last pre-delivery snapshot (D025)
- Data version: P3 target + P4.2 revision + P5 H1-B proxy

### Information snapshot

- Renewable forecast revision: H2 5h->1h wind revision — real but weak
  (Spearman ~ -0.10), asymmetric (works on DOWN, not UP), fails at low wind, did
  not reproduce on 2024 H1
- Residual-load condition: H1 actual is diagnostic and weak/threshold-like; the
  H1-B climatology proxy tracks actual residual load (Spearman +0.92) but its own
  spread association is as weak as H1-A
- Cross-border condition: H3 shows no decision-eligible conditioning; only a weak
  diagnostic effect via realized net-import flow

### Market view

- Directional view: mostly No Trade — the transparent engine takes an active view
  in 33% of valid hours
- Confidence: Low to Medium; nothing supports High
- Main driver: the H2 DOWN side plus the H1 tight-system UP side
- Counterargument: hourly balancing outcomes are dominated by shocks the eligible
  inputs cannot see
- Key risk: reading a weak in-sample signal as a deployable edge

### Decision

- Decision: retain H2 as conditionally supported, H1 as a weak diagnostic with an
  eligible proxy, H3 as diagnostic-only; build a probabilistic model before any
  stronger claim
- No-Trade condition: conflicting or silent views, missing eligible input
- Invalidation condition: the H2 gradient failing to reproduce on the locked
  holdout at Level C

### Outcome

- Signal balanced accuracy 0.347 vs majority
  0.333 (full sample, No Trade = NEUTRAL); active-view
  three-class hit rate 0.289 over
  7,154 hours
- Baseline result: the signal edges the availability-safe baselines on balanced
  accuracy but the margin is small and in-sample

### Post-Mortem

- What was correct: pre-registration held; every hypothesis got one honest round;
  nulls and weaknesses were kept
- What was wrong / missing: no demand-shock or outage information; the round-1
  baseline gate (P4.3) was too lenient
- Was the original reasoning valid: yes for the mechanism, no for any deployable
  claim
- What should change: stricter baselines, a probabilistic model with calibration
  (P10), then the one-shot holdout test
