# Project Status / 项目进度

**Project:** DK1 Short-Term Power Market Research
**Last updated:** 2026-09-06
**Design baseline:** Frozen MVP Blueprint v1.1

## Current Position / 当前定位

| Item | Current Status |
|---|---|
| Completed phase | P0 — Project Control & Environment |
| Current phase | P1 — Data Source Validation |
| Current step | P1.4 — Validate fundamentals and system sources |
| Next step | P2.1 — Implement reproducible development-data acquisition |
| Current milestone | Level A — CV-safe |
| Milestone status | NOT ACHIEVED |
| Holdout | LOCKED and unused |
| Blocker | None |

## One Current Action / 当前唯一动作

Validate candidate demand, generation, cross-border and system-condition
sources, including field meaning and point-in-time eligibility.

核验需求、发电、跨境和系统条件候选来源，包括字段含义和 point-in-time 资格。

## P1.1 Completion / Forecasts_Hour 核验结论

**Status:** CONDITIONAL PASS — completed 2026-09-06

- Official dataset ID, fields, units, DK1 selector and forecast types registered
- Full local-date development boundary validated with zero holdout records
- `HourUTC + PriceArea + ForecastType` validated as the canonical key
- Same-row 5h-to-1h revision is feasible with approximately 99% numeric pair coverage
- Missing rows and nulls must be excluded and never filled with zero
- Observed zero and negative forecasts must be preserved with quality flags
- Solar requires an all-pairs view and a both-positive sensitivity view
- UTC is required for joins; local time is retained for DST interpretation
- `TimestampUTC` belongs to `ForecastCurrent`, not the 5h/1h publication times
- Fixed-horizon research is supported; complete tick-by-tick vintage claims are prohibited
- Exact simulated decision cutoff remains an explicit P2.3 item

## P1.2 Completion / DK1 Day-Ahead Price 核验结论

**Status:** PASS — completed 2026-09-06

- Official legacy dataset `Elspotprices` (ID 30) registered for the declared period
- `SpotPriceEUR` selected as `P_DayAhead,t` in EUR/MWh
- Full local-date development boundary contains all 21,887 expected hours
- Zero missing hours, zero duplicate primary-key rows and zero holdout rows
- `HourUTC + PriceArea` validated as the canonical key; filter area to DK1
- `HourDK` retained for interpretation and DST checks only
- Zero and negative day-ahead prices preserved as market observations
- `SpotPriceDKK` retained for audit but excluded from the EUR spread
- Exact row-level publication timestamps are unavailable and remain in P2.3
- Future data after 2025-09-30 requires the successor `DayAheadPrices` dataset

## P1.3 Completion / DK1 Balancing Outcome 核验结论

**Status:** CONDITIONAL PASS — completed 2026-09-06

- Official legacy dataset `RegulatingBalancePowerdata` (ID 122) registered
- `ImbalancePriceEUR` selected as `P_Balancing,t` in EUR/MWh
- Target classified as an ex-post `outcome`, never a decision-time feature
- All 21,886 returned development rows contain the selected target price
- Every target value matches the official Up price, Down price or both
- One of 21,887 expected hours is absent: `2022-10-30T00:00:00Z`
- A separate bounded official API request confirmed the same DST fall-back gap
- Zero duplicate-key rows, zero extra rows and zero holdout rows
- Missing row must remain missing; zero, negative and extreme prices are retained
- Nordic single-price go-live on 2021-11-01 precedes the whole development period
- Active 15-minute `ImbalancePrice` successor starts in 2025 and is not mixed in
- Exact historical publication delay is undocumented and remains under I03/P2.3
- Outcome is a balancing-pressure proxy, not executable trading P&L

## Completed Setup / 已完成搭建

- [x] Formal local Git repository created
- [x] Default branch set to `main`
- [x] Repository moved to the central Projects directory
- [x] `.gitignore` created
- [x] Repository directory structure created
- [x] Python 3.12 pinned
- [x] Project-specific `.venv` created
- [x] Core Python dependencies installed
- [x] `pyproject.toml` and `uv.lock` created
- [x] Professional README created
- [x] Project Charter created
- [x] Research Config created and validated
- [x] Project-control documents added
- [x] Data Dictionary initialized
- [x] Hypothesis Registry initialized
- [x] Market Journal initialized
- [x] Setup quality checks passed

## Level A Evidence Board / Level A 证据板

| # | Criterion | Status |
|---|---|---|
| A1 | Repository | DONE |
| A2 | Professional README | DONE |
| A3 | Project Charter | DONE |
| A4 | Target, development and holdout config | DONE |
| A5 | Forecast, day-ahead and balancing data | DONE — all three core sources validated with documented conditions |
| A6 | Data Dictionary and PIT classification | DONE — core forecast, reference and outcome fields registered |
| A7 | H2 revision variables | NOT STARTED |
| A8 | At least one completed hypothesis test | NOT STARTED |
| A9 | At least one meaningful chart | NOT STARTED |
| A10 | Holdout completely unused | MAINTAINED |

**Level A: NOT ACHIEVED**
**Level B: NOT ACHIEVED**
**Level C: NOT ACHIEVED**

## Frozen Research Controls / 冻结研究规则

- Development period: 2022-01-01 to 2024-06-30
- Locked holdout: 2024-07-01 to 2024-12-31
- Target: `Spread_t = P_Balancing,t - P_DayAhead,t`
- Neutral band: development-only Q25 of nonzero absolute spreads
- Mandatory baselines: majority class and persistence
- Primary MVP hypothesis: H2 renewable forecast revision
- No executable intraday P&L claim
- Holdout access remains prohibited

## Prepared Reference / 参考版本

Earlier assistant-prepared P1.1 files remain outside the formal repository as reference material and did not count as completion evidence. The formal P1.1 was subsequently performed, reviewed and recorded through the guided process in this repository.

## Session Log / 工作记录

| Date | Completed | Current / Next |
|---|---|---|
| 2026-09-05 | P0 repository and environment setup completed | Current: P1.1; Next: P1.2 |
| 2026-09-06 | P1.1 `Forecasts_Hour` completed with a conditional pass | Current: P1.2; Next: P1.3 |
| 2026-09-06 | P1.2 `Elspotprices` completed with a pass | Current: P1.3; Next: P1.4 |
| 2026-09-06 | P1.3 `RegulatingBalancePowerdata` completed with a conditional pass | Current: P1.4; Next: P2.1 |

Update this file after every completed work session. Every DONE status requires reviewed evidence.
