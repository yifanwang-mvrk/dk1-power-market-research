# Data Dictionary

**Project:** DK1 Short-Term Power Market Research
**Status:** P1.1 completed; `Forecasts_Hour` conditionally validated
**Last updated:** 2026-09-06

## Field Registry

| Dataset | Field | Business Meaning | Unit | Time Meaning | PIT Class | Evidence Status |
|---|---|---|---|---|---|---|
| Forecasts_Hour | HourUTC | Start of the forecast delivery hour in UTC | — | Delivery interval; canonical join time | decision_eligible (key) | Validated P1.1 |
| Forecasts_Hour | HourDK | Start of the forecast delivery hour in Danish local time | — | Delivery interval; DST interpretation only | decision_eligible (key) | Validated P1.1; not sole join key |
| Forecasts_Hour | PriceArea | Danish bidding zone | text | Static area selector | decision_eligible (key) | Validated P1.1; use DK1 |
| Forecasts_Hour | ForecastType | Forecasted production category: Solar, Offshore Wind or Onshore Wind | text | Static category selector | decision_eligible (key) | Validated P1.1 |
| Forecasts_Hour | ForecastDayAhead | Renewable-production forecast for the next day | MWh per hour | Generated at 17:50 and published at 18:00 Danish time according to official metadata | pending cutoff | Validated definition; outside primary H2 signal |
| Forecasts_Hour | ForecastIntraday | Renewable-production forecast for the coming day at 06:00 Danish time | MWh per hour | Intraday horizon; exact historical eligibility depends on delivery hour and cutoff | pending cutoff | Excluded from primary H2 pending further evidence |
| Forecasts_Hour | Forecast5Hour | Renewable-production forecast valid five hours ahead | MWh per hour | Fixed 5-hour horizon snapshot; exact minute timestamp is not stored | decision_eligible (conditional) | Validated for H2 subject to P2.3 cutoff |
| Forecasts_Hour | Forecast1Hour | Renewable-production forecast valid one hour ahead | MWh per hour | Fixed 1-hour horizon snapshot; exact minute timestamp is not stored | decision_eligible (conditional) | Validated for H2 subject to P2.3 cutoff |
| Forecasts_Hour | ForecastCurrent | Renewable-production forecast valid for the current delivery time | MWh per hour | Current-time forecast associated with TimestampUTC | diagnostic_only | Excluded from pre-delivery H2 signal |
| Forecasts_Hour | TimestampUTC | UTC generation timestamp for ForecastCurrent | — | Current-forecast generation time; not the 5h or 1h publication time | diagnostic_only | Validated P1.1 |
| Forecasts_Hour | TimestampDK | Danish-local generation timestamp for ForecastCurrent | — | Local equivalent of TimestampUTC | diagnostic_only | Validated P1.1; DST interpretation only |

## Point-in-Time Classes

- `decision_eligible`: available at the simulated decision time
- `diagnostic_only`: useful for explanation but unavailable for the decision
- `outcome`: known only after the delivery period

`decision_eligible (conditional)` means the field is a pre-delivery horizon
candidate, but the exact simulated decision cutoff must be locked in P2.3
before signal evaluation.

## P1.1 Dataset Contract

- Dataset ID: `40`
- Dataset name: `Forecasts_Hour`
- Source: Energinet Energi Data Service
- Resolution: one hour (`PT1H`)
- Official primary key: `HourUTC`, `PriceArea`, `ForecastType`
- DK1 forecast types: `Offshore Wind`, `Onshore Wind`, `Solar`
- Development request boundary: local `2022-01-01 00:00` inclusive to local
  `2024-07-01 00:00` exclusive
- Canonical time key: `HourUTC`
- Interpretation timezone: `Europe/Copenhagen`
- 5h-to-1h revision rule: calculate only within the same primary-key row and
  only when both horizon fields are non-null
- Missing-row and null policy: flag and exclude; never impute as zero
- Observed-zero and negative policy: preserve with quality flags; do not
  silently coerce
- Solar sensitivity: report both all numeric pairs and pairs where both
  horizons are positive
- Vintage claim: fixed-horizon snapshots only; no complete tick-by-tick
  publication history

## P1.1 Coverage Evidence

| Forecast type | Expected hours | Whole-row coverage | 5h/1h pair coverage | Whole-row missing hours |
|---|---:|---:|---:|---:|
| Offshore Wind | 21,887 | 99.7396% | 98.9948% | 57 |
| Onshore Wind | 21,887 | 99.7396% | 98.8578% | 57 |
| Solar | 21,887 | 99.7807% | 98.9811% | 48 |

The complete evidence and handling rules are recorded in
`research/evidence/p1_1_forecasts_hour/development_validation_2026-09-06.md`.

## Registration Rules

- Do not classify a field as decision eligible only because it appears in historical data.
- Record the official definition, unit and timestamp meaning.
- Use `HourUTC` as the canonical join key unless source validation establishes otherwise.
- Retain Danish local time for interpretation and daylight-saving checks.
- Record missing values and duplicate keys explicitly.
- Do not convert missing values to zero without documented evidence.
- Do not access or register fields from the locked holdout before its formal unlock.
