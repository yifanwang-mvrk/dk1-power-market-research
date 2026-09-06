# Project Status / 项目进度

**Project:** DK1 Short-Term Power Market Research
**Last updated:** 2026-09-06
**Design baseline:** Frozen MVP Blueprint v1.1

## Current Position / 当前定位

| Item | Current Status |
|---|---|
| Completed phase | P1 — Data Source Validation |
| Current phase | P2 — Data Pipeline |
| Current step | P2.1 — Implement reproducible development-data acquisition |
| Next step | P2.2 — Preserve raw data and provenance |
| Current milestone | Level A — CV-safe |
| Milestone status | NOT ACHIEVED |
| Holdout | LOCKED and unused |
| Blocker | None |

## One Current Action / 当前唯一动作

Build a date-bounded API client that cannot cross the development boundary and
prove it on development-only samples with explicit failure handling.

实现不会越过 development 边界的 API client，并用 development-only 小样本和明确的失败处理证明它可重复运行。

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

## P1.4 Completion / Fundamentals and System Sources 核验结论

**Status:** PASS — completed 2026-09-06

- `ProductionConsumptionSettlement` passed all development-boundary, key and
  completeness checks with 21,887 DK1 hours and zero holdout rows
- Actual wind, actual solar and actual residual load were defined for H1-A and
  classified `diagnostic_only` because settlement values arrive after delivery
- Negative actual residual load occurs in 5,974 hours and is preserved as a
  physical observation rather than treated as missing
- Actual cross-border settlement fields are diagnostic; GB source-defined
  historical nulls remain null
- `Transmissionlines` covers all development hours and six DK1 connections
- Day-ahead capacities and `ScheduledExchangeDayAhead` are conditional
  decision candidates pending exact P2.3 cutoff mapping and P6.1 border rules
- Mixed `ExportCapacity` signs and unavailable GB day-ahead fields are
  documented conditions, not silently repaired
- Final intraday schedules and physical exchange are diagnostic only
- Legacy `CountertradeIntraday` is a partial-period conditional candidate:
  7,447 of 7,751 final rows were published at least one hour before delivery,
  while overwritten earlier versions cannot be reconstructed
- The 2025 countertrade successor is unavailable for the development period
- No validated Energi Data Service historical load forecast was identified;
  the ENTSO-E day-ahead load forecast remains an external P5.2 candidate
- Reserve-capacity and real-time sources were registered with explicit
  candidate or diagnostic status; no unvalidated field was promoted
- A reproducible validator, raw-data manifests and a machine-readable source
  eligibility inventory are preserved under `research/evidence/p1_4_sources/`
- Holdout remained locked and unused; missing values were never converted to zero

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
| A6 | Data Dictionary and PIT classification | DONE — core and P1.4 source fields registered by eligibility class |
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
| 2026-09-06 | P1.4 fundamentals, cross-border and system-source inventory completed with a pass | Current: P2.1; Next: P2.2 |

Update this file after every completed work session. Every DONE status requires reviewed evidence.
