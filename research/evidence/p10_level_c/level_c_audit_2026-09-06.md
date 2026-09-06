# P10.4 — Level C Acceptance Audit

**Date:** 2026-09-06
**Auditor pass:** each criterion checked against committed evidence at
`git HEAD = 4a0623d` (the P10.3 commit) plus the P10.4 documentation.
**Result: 10 / 10 criteria met — Level C (MVP v1 Complete) ACHIEVED.**
**Holdout:** EVALUATED ONCE (D037), then closed — `state: evaluated`,
`fetch_allowed: false`.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| C1 | Logistic Regression baseline | DONE | P10.1 (D035): multinomial LR, `C=1.0`, 10 decision-eligible features, time-ordered development split, Platt calibration; right coefficient signs, no 2024 H1 validation edge. `research/evidence/p10_model/` |
| C2 | Locked holdout unlocked under the protocol | DONE | P10.2 (D036): spec frozen at commit `47577b1`, unlock template completed, prior non-use machine-verified. P10.3 (D037): owner-approved unlock 2026-09-06, evaluated once, config re-locked as `evaluated`. `research/evidence/p10_holdout_unlock/`, `research/evidence/p10_holdout/` |
| C3 | Out-of-sample evaluation on 2024 H2 | DONE | P10.3: 4,417 holdout hours, 4,331 scored; `p10_3_holdout_result_2026-09-06.json` |
| C4 | Comparison vs majority baseline (holdout) | DONE | Calibrated logistic balanced accuracy 0.352 vs majority 0.333; macro-F1 0.297 vs 0.247 |
| C5 | Comparison vs persistence (holdout) | DONE | Persistence 0.635 balanced accuracy, reported as an ex-post reference (D023 / E001); the model sits far below it |
| C6 | Probability calibration + assessment | DONE | Platt calibrator frozen in P10.1; holdout multiclass Brier 0.593 vs a 0.582 development-class-frequency reference (no skill); calibration curve `p10_3_holdout_calibration_2026-09-06.png` |
| C7 | Regime performance (holdout) | DONE | By meteorological season (summer 0.362, winter 0.326) and by wind-forecast tercile; `by_season` / `by_wind_level` in the result JSON |
| C8 | Limitations | DONE | `research/r01_research_memo.md` §10; weak effect, no probability skill, ~2-point edge within sampling range, no demand-shock information, H3 diagnostic-only, not deployable P&L (D016) |
| C9 | Full research memo | DONE | `research/r01_research_memo.md` v1.1 — question, method, H1/H2/H3, the signal, the model, the holdout result and its limitations, and what a next round would change |
| C10 | Polished README | DONE | `README.md` — MVP v1 Complete status, the H2 result, the locked-holdout result table, reproduction commands, research principles; no deployable-signal or profit language (D016 / D018) |

## The result, in one paragraph

Renewable wind-forecast revisions carry a small amount of directionally correct
information about DK1 balancing pressure, concentrated on the downward side and
present mainly when wind is a material factor. It survived the locked-holdout
test only marginally: the frozen calibrated logistic beats the availability-safe
baselines by about two points on balanced accuracy and macro-F1, with no
probability skill and far below the ex-post persistence reference. The mechanism
is real and did not vanish out of sample, but it is not an edge worth acting on.

## Verdict

Level C — MVP v1 Complete: **ACHIEVED**. A finding of a marginal, non-deployable
edge completes the MVP exactly as a positive or a null result would; the value is
the point-in-time discipline, the pre-registration, the untouched-until-once
holdout, and reporting the result as produced. Decision D038.
