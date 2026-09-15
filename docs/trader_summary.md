# DK1 Balancing-Pressure Signal — Trader Summary

*A 3-minute read of [`research/r01_research_memo.md`](../research/r01_research_memo.md). Full evidence: [`README.md`](../README.md), [`docs/final_project_audit_2026-09-06.md`](final_project_audit_2026-09-06.md).*

**Bottom line: the mechanism is real, but it is not a deployable signal.** It survived an out-of-sample test only marginally, has no usable probability skill, and stays far below a naive persistence reference. This memo is being shared for the research discipline, not as a trade recommendation.

## The question

Do renewable (mostly wind) forecast revisions and observable system conditions carry information about which way DK1 balancing prices will move relative to day-ahead, hour by hour — and where does that relationship break down?

`Spread = Balancing price − Day-ahead price (EUR/MWh)`, classified UP / DOWN / NEUTRAL around a frozen neutral band of ±5.9956075 EUR/MWh.

## How the decision point is defined

Every input is timestamped and classified before it is used:

- **Decision cutoff:** the last information snapshot *strictly before* the delivery hour starts. Only forecasts published before that moment are usable — the model does not see anything published during or after the hour it is predicting.
- **Eligible at decision time:** fixed 5h/1h-ahead wind and solar forecasts, day-ahead cross-border capacity/schedule.
- **Not eligible (diagnostic or outcome only):** actual realized wind/solar/demand, realized cross-border flows, the balancing price itself — all published after the fact.
- **Two time windows, kept apart:** the model was built and tuned only on 2022-01-01 → 2024-06-30. 2024-07-01 → 2024-12-31 was locked and untouched until one single, pre-approved evaluation run — the standard a systematic strategy would need to pass before risking capital.

## The result

The primary driver — a rise in the wind forecast between 5h and 1h ahead of delivery — does push the outcome toward DOWN, monotonically, across the whole development period:

| Wind-revision quintile | P(UP) | P(DOWN) |
|---|---:|---:|
| Most negative revision | 24.7% | 27.3% |
| Most positive revision | 17.2% | 38.7% |

That gradient is statistically real (permutation test, p ≈ 0), but small (Spearman ≈ −0.10), one-sided (DOWN only — it says almost nothing about UP), and it disappears when wind is already scarce.

**The locked-holdout test (2024 H2, 4,331 hours, run once):**

| Method | Balanced accuracy | Macro-F1 |
|---|---:|---:|
| Calibrated model | **0.352** | **0.297** |
| Naive baseline (majority class) | 0.333 | 0.247 |
| Naive baseline (hour-of-week) | 0.329 | 0.280 |
| Persistence (ex-post reference, not tradeable) | 0.635 | 0.635 |

## Why this is judged non-deployable

- **The edge is barely above noise.** ~2 points of balanced accuracy over a naive baseline, on 4,331 hours — within the range random sampling alone can produce.
- **No probability skill.** The model's calibrated probabilities score worse (Brier 0.593) than simply using the historical class frequencies (0.582). You cannot size a position off these probabilities.
- **It mostly says nothing.** It predicts NEUTRAL 95% of the time; the entire usable signal is concentrated in a small set of DOWN calls (49% hit rate vs. a 27% base rate).
- **Far below the naive persistence reference (0.635).** Persistence itself isn't executable (its source timing isn't documented), but it shows how much easier signal is left on the table than what this model captures.
- **It did not reproduce on the nearest out-of-time slice** (2024 H1, used during development) before the holdout even confirmed a small edge — a warning sign the effect is fragile, not a stable structural relationship.
- **The inputs can't see what actually moves balancing prices** — outages, demand surprises, realized cross-border flows. None of that is decision-eligible at the cutoff this study enforces.

## Why the "no" is trustworthy

The negative result comes from a research process built specifically to prevent a false positive: point-in-time field classification, a target frozen before any hypothesis touched an outcome, a pre-registered primary test, mandatory naive baselines, and a holdout locked until one single approved run. The project's value is that discipline and an honest result — not a trading edge.

## Where to go deeper

- Full narrative and limitations: [`research/r01_research_memo.md`](../research/r01_research_memo.md)
- Repository status and reproduction steps: [`README.md`](../README.md)
- Independent verification of every claim above: [`docs/final_project_audit_2026-09-06.md`](final_project_audit_2026-09-06.md)
- Raw holdout evidence: [`research/evidence/p10_holdout`](../research/evidence/p10_holdout/README.md)
