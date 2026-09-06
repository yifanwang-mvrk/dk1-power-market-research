# Project Status / 项目进度

**Project:** DK1 Short-Term Power Market Research
**Last updated:** 2026-09-06
**Design baseline:** Frozen MVP Blueprint v1.1

## Current Position / 当前定位

| Item | Current Status |
|---|---|
| Completed phase | P3 — Target Construction |
| Current phase | P4 — H2 Renewable Forecast Revision |
| Current step | P4.2 — Build wind/solar 5h-to-1h revisions on the P2 base |
| Next step | P4.3 — Run the pre-registered round-1 test and chart |
| Current milestone | Level A — CV-safe |
| Milestone status | NOT ACHIEVED |
| Holdout | LOCKED and unused |
| Blocker | None |

## One Current Action / 当前唯一动作

Build the wind and solar 5h-to-1h revision variables on the P2 hourly base per
the frozen P4.1 spec: same-hour non-null pairs only, the `5h == 1h` and coverage
diagnostics, and the frozen five-quantile / ten-decile bucket edges — before any
revision-outcome comparison.

按冻结的 P4.1 规格，在 P2 小时底表上构造 wind 和 solar 的 5h→1h revision 变量：
只用同小时非空配对，产出 `5h == 1h` 与覆盖率诊断，并冻结五分位 / 十分位分箱边界，
然后再做任何 revision 与结果的比较。

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

## P2 Completion / Development Data Pipeline 完成结论

**Status:** PASS — P2.1 through P2.5 completed 2026-09-06

- P2.1 added a reusable Energi Data Service client that rejects pre-development,
  holdout, non-DK1 and unbounded area requests before network access
- A live DK1 development-only day sample returned all 24 expected hourly spot
  rows; automated checks cover 429 retry handling and truncated responses
- P2.2 preserved six exact P1 raw JSON responses with request, retrieval and
  SHA-256 provenance; every current hash matches its P1 manifest
- P2.3 standardized local-date request boundaries, UTC joins, Danish-local
  interpretation, UTC offsets and repeated DST-hour occurrence
- The decision anchor is `delivery_start_utc`; only information available
  strictly before that anchor belongs to the last-pre-delivery snapshot
- Non-null `Forecast5Hour` and `Forecast1Hour` values are eligible at that
  snapshot under the official pre-delivery availability rule; no exact-minute
  or complete-vintage claim is made
- `ImbalancePriceEUR` remains an outcome; actual settlement fundamentals and
  realized flows remain diagnostic only
- Day-ahead transmission fields pass the timing gate but remain conditional on
  P6.1 border/sign rules
- Countertrade uses `PublicationDate < delivery_start_utc`; 7,469 of 7,751
  stored rows pass, while 282 fail the cutoff and absent days remain unknown
- Previous-hour spread/label persistence remains an ex-post reference because
  the legacy outcome publication delay is undocumented
- P2.4 produced a local 93-column hourly base with 21,887 unique DK1 hours
- P2.5 passed all boundary, key, DST, coverage, unit and eligibility checks
- Spot price has zero gaps; the single balancing gap at
  `2022-10-30T00:00:00Z` remains null; holdout rows remain zero
- Evidence: `research/evidence/p2_data_pipeline/`; local processed table:
  `data/processed/p2/hourly_base_development.parquet`

## P3 Completion / Target Construction 完成结论

**Status:** PASS — P3.1 through P3.4 completed 2026-09-06

- P3.1 built the same-hour target
  `balancing_spread_eur_mwh = imbalance_price_eur_mwh - spot_price_eur_mwh` on the
  P2 base: 21,886 valid spreads, 6,494 exact zeros, 6,345 positive and 9,047
  negative; the one documented gap at `2022-10-30T00:00:00Z` is preserved as a
  missing spread
- P3.2 froze `delta = 5.9956075 EUR/MWh`, the pandas linear-interpolation Q25 of
  15,392 nonzero absolute development spreads; the one missing spread and the
  6,494 observed-zero spreads are excluded from the quantile population
- The frozen value, method, nonzero population, input SHA-256 and library
  versions are recorded in `config/research_config.yaml` with
  `holdout_may_influence: false`
- P3.3 assigned 4,354 UP, 7,190 DOWN and 10,342 NEUTRAL labels plus one missing
  label; both exact `±delta` boundaries and observed zeros are NEUTRAL; no
  missing value is zero-filled
- P3.4 fixed the baseline contracts: the majority baseline is fit on training
  labels only; the frozen persistence formula stays an ex-post reference because
  the legacy outcome publication delay is undocumented;
  `hour_of_week_training_majority` is registered as the availability-safe
  supplemental baseline before evaluation
- Quality gate: 13/13 critical checks; target table 21,887 rows and 99 columns;
  zero holdout rows; 13/13 test suite passes
- Decision: D026; resolves I05 and the P3.4 portion of I03
- Evidence: `research/evidence/p3_target_construction/`; local processed table:
  `data/processed/p3/target_development.parquet`

## P4.1 Completion / H2 Pre-Registration 完成结论

**Status:** DONE — H2 round-1 test pre-registered 2026-09-06, before any revision
variable was constructed

- Primary test: `wind_revision_t = (Offshore + Onshore) Forecast1Hour - Forecast5Hour`
  in raw MWh, same-hour non-null pairs only; this test alone decides "H2 supported"
- Solar runs the identical procedure as a separate secondary test; a solar-only
  pass is "conditionally supported — solar only, needs replication"
- Expected direction: positive wind revision favours DOWN, negative favours UP;
  contrary and null outcomes are admissible and must be reported
- Buckets: development-only signed quantiles Q20/Q40/Q60/Q80 (primary) plus a
  ten-decile secondary view, frozen in P4.2 before any outcome comparison
- Method: bucket × label contingency table; Spearman association (primary vs the
  continuous signed spread, secondary vs the +1/0/-1 label score) with bootstrap
  CI; one transparent rule with `c` = development Q60 magnitude; one chart
- Pass/fail gate: the rule must beat majority and hour-of-week on balanced
  accuracy and macro-F1; persistence is reported prominently but is an ex-post
  reference (D023, E001), not a gate
- Evidence: `research/evidence/p4_h2_revision/` and
  `research/hypotheses.md` (H2 section)

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
| A4 | Target, development and holdout config | DONE — periods, target fields and the frozen Q25 delta (5.9956075 EUR/MWh) all in research config |
| A5 | Forecast, day-ahead and balancing data | DONE — all three core sources validated with documented conditions |
| A6 | Data Dictionary and PIT classification | DONE — core and P1.4 source fields registered by eligibility class |
| A7 | H2 revision variables | IN PROGRESS — round-1 test pre-registered (P4.1); variables built in P4.2 |
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
- Neutral band: development-only Q25 of nonzero absolute spreads = 5.9956075 EUR/MWh (frozen 2026-09-06, before holdout access)
- Mandatory baselines: majority class and persistence (persistence is ex-post reference; hour-of-week training majority is the availability-safe supplement)
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
| 2026-09-06 | P2.1–P2.5 bounded acquisition, provenance, time normalization, hourly joining and quality gates completed | Current: P3.1; Next: P3.2 |
| 2026-09-06 | P3.1–P3.4 balancing spread built, Q25 delta frozen at 5.9956075 EUR/MWh, three labels assigned, baseline contracts fixed (D026) | Current: P4.1; Next: P4.2 |
| 2026-09-06 | P4.1 H2 round-1 test pre-registered (wind primary, solar secondary; signed-quantile buckets; Spearman + transparent rule; gate = majority + hour-of-week) | Current: P4.2; Next: P4.3 |

Update this file after every completed work session. Every DONE status requires reviewed evidence.
