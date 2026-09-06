# Data Dictionary

**Project:** DK1 Short-Term Power Market Research
**Status:** P1.1-P1.3 completed; forecast, day-ahead and balancing sources registered
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
| Elspotprices | HourUTC | Start of the price delivery hour in UTC | — | Delivery interval; canonical join time | decision_eligible (key) | Validated P1.2 |
| Elspotprices | HourDK | Start of the price delivery hour in Danish local time | — | Delivery interval; DST interpretation only | decision_eligible (key) | Validated P1.2; not sole join key |
| Elspotprices | PriceArea | Bidding zone for the area price | text | Static area selector | decision_eligible (key) | Validated P1.2; use DK1 |
| Elspotprices | SpotPriceDKK | Day-ahead spot price in the price area | DKK/MWh | Price for the delivery hour, formed in the preceding day-ahead market | decision_eligible (reference audit) | Validated P1.2; not selected for spread |
| Elspotprices | SpotPriceEUR | Day-ahead spot price in the price area | EUR/MWh | Price for the delivery hour, formed in the preceding day-ahead market | decision_eligible (reference) | Validated P1.2; selected as P_DayAhead,t |
| RegulatingBalancePowerdata | HourUTC | Start of the balancing delivery hour in UTC | — | Delivery interval; canonical outcome join time | outcome (key) | Validated P1.3 |
| RegulatingBalancePowerdata | HourDK | Start of the balancing delivery hour in Danish local time | — | Delivery interval; DST interpretation only | outcome (key) | Validated P1.3; not sole join key |
| RegulatingBalancePowerdata | PriceArea | Bidding zone for the balancing outcome | text | Static area selector | outcome (key) | Validated P1.3; use DK1 |
| RegulatingBalancePowerdata | ImbalancePriceEUR | Official imbalance price based on the dominating direction | EUR/MWh | Final price outcome for the delivery hour | outcome | Validated P1.3; selected as P_Balancing,t |
| RegulatingBalancePowerdata | BalancingPowerPriceUpEUR | Official upward balancing-power price component | EUR/MWh | Final directional price for the delivery hour | outcome (audit) | Validated P1.3; not independently selected as target |
| RegulatingBalancePowerdata | BalancingPowerPriceDownEUR | Official downward balancing-power price component | EUR/MWh | Final directional price for the delivery hour | outcome (audit) | Validated P1.3; not independently selected as target |
| RegulatingBalancePowerdata | ImbalanceMWh | Imbalance remaining after TSO activation of mFRR, aFRR and FCR | MWh | Ex-post physical-system diagnostic | outcome (diagnostic) | Validated P1.3; do not infer official direction from sign alone |
| RegulatingBalancePowerdata | mFRRUpActBal | Danish mFRR activation for upward balancing | MWh | Ex-post activation volume | outcome (diagnostic) | Validated definition P1.3 |
| RegulatingBalancePowerdata | mFRRDownActBal | Danish mFRR activation for downward balancing | MWh | Ex-post activation volume | outcome (diagnostic) | Validated definition P1.3 |

## Point-in-Time Classes

- `decision_eligible`: available at the simulated decision time
- `diagnostic_only`: useful for explanation but unavailable for the decision
- `outcome`: known only after the delivery period

`decision_eligible (conditional)` means the field is a pre-delivery horizon
candidate, but the exact simulated decision cutoff must be locked in P2.3
before signal evaluation.

`decision_eligible (reference)` means the field is an already-established
pre-delivery benchmark used in the target definition. Exact availability
mapping remains part of the P2.3 timestamp contract.

## P1.1 Dataset Contract

- Dataset ID: `40`
- Dataset name: `Forecasts_Hour`
- Source: Energinet Energi Data Service
- License: CC BY 4.0; attribute published use to Energinet
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

## P1.2 Dataset Contract

- Dataset ID: `30`
- Dataset name: `Elspotprices`
- Source: Energinet Energi Data Service
- License: CC BY 4.0; attribute published use to Energinet
- Resolution: one hour (`PT1H`)
- Official primary key: `HourUTC`, `PriceArea`
- Area selector: `DK1`
- Selected field: `SpotPriceEUR`
- Selected unit: `EUR per MWh`
- Target role: `P_DayAhead,t` in
  `Spread_t = P_Balancing,t - P_DayAhead,t`
- Canonical time key: `HourUTC`
- Interpretation timezone: `Europe/Copenhagen`
- Missing policy: preserve missingness; never impute a missing price as zero
- Value policy: preserve zero and negative prices as market observations
- Currency policy: retain `SpotPriceDKK` for audit, but do not mix DKK and EUR
  in the spread
- Source lifecycle: this legacy dataset is discontinued after 2025-09-30;
  later extensions must separately validate its `DayAheadPrices` successor

## P1.2 Coverage Evidence

| Expected hours | Returned rows | Missing | Duplicate key rows | Holdout rows |
|---:|---:|---:|---:|---:|
| 21,887 | 21,887 | 0 | 0 | 0 |

The development period contains 76 zero and 503 negative EUR prices. They are
retained as valid observations rather than treated as missing or errors. The
complete evidence and handling rules are recorded in
`research/evidence/p1_2_elspotprices/development_validation_2026-09-06.md`.

## P1.3 Dataset Contract

- Dataset ID: `122`
- Dataset name: `RegulatingBalancePowerdata`
- Source: Energinet Energi Data Service
- License: CC BY 4.0; attribute published use to Energinet
- Source lifecycle: discontinued legacy hourly dataset
- Resolution: one hour (`PT1H`)
- Official primary key: `HourUTC`, `PriceArea`
- Area selector: `DK1`
- Selected field: `ImbalancePriceEUR`
- Selected unit: `EUR per MWh`
- Target role: `P_Balancing,t` in
  `Spread_t = P_Balancing,t - P_DayAhead,t`
- PIT class: `outcome`; unavailable to the simulated pre-delivery decision
- Canonical time key: `HourUTC`
- Interpretation timezone: `Europe/Copenhagen`
- Official logic: based on the dominating direction; Up uses the maximum of
  the aFRR component or mFRR price, None uses avoided-activation value / spot
  price, and Down uses the minimum of the aFRR component or mFRR price
- Directional-price policy: retain Up and Down EUR fields for audit; do not
  choose a direction after observing the research result
- Missing policy: preserve the absent full row; never create or zero-fill it
- Value policy: preserve zero, negative and extreme prices with quality flags
- Currency policy: use EUR; the official source cautions that DKK Up/Down
  values are missing
- Historical regime: the Nordic single-price model went live on 2021-11-01,
  before the development period
- Publication limitation: the discontinued source reports update frequency as
  N/A and does not document an exact historical publication delay
- Successor limitation: active `ImbalancePrice` begins in 2025 at 15-minute
  resolution and does not cover the declared development period

## P1.3 Coverage Evidence

| Expected hours | Returned rows | Target nulls | Missing rows | Duplicate key rows | Holdout rows |
|---:|---:|---:|---:|---:|---:|
| 21,887 | 21,886 | 0 | 1 | 0 | 0 |

The missing row is `2022-10-30T00:00:00Z`, the first repeated local 02:00
hour on the DST fall-back day. A separate bounded official request confirmed
the same gap. Across all returned rows, `ImbalancePriceEUR` matches the Up
price only in 5,290 hours, the Down price only in 7,900, and both prices in
8,696; it matches neither in zero hours. The complete evidence is recorded in
`research/evidence/p1_3_regulating_balance_power/development_validation_2026-09-06.md`.

## Registration Rules

- Do not classify a field as decision eligible only because it appears in historical data.
- Record the official definition, unit and timestamp meaning.
- Use `HourUTC` as the canonical join key unless source validation establishes otherwise.
- Retain Danish local time for interpretation and daylight-saving checks.
- Record missing values and duplicate keys explicitly.
- Do not convert missing values to zero without documented evidence.
- Do not access or register fields from the locked holdout before its formal unlock.
