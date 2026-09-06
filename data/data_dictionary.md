# Data Dictionary

**Project:** DK1 Short-Term Power Market Research
**Status:** P3 completed; target, neutral band and labels frozen on development data
**Last updated:** 2026-09-06

## Field Registry

| Dataset | Field | Business Meaning | Unit | Time Meaning | PIT Class | Evidence Status |
|---|---|---|---|---|---|---|
| P3 target | balancing_spread_eur_mwh | Realized balancing pressure relative to the already-cleared day-ahead reference | EUR/MWh | Same-hour `ImbalancePriceEUR - SpotPriceEUR` | outcome | P3.1 PASS; 21,886 valid values and one preserved source gap |
| P3 target | absolute_spread_eur_mwh | Magnitude of the realized balancing spread | EUR/MWh | Absolute value of the same-hour outcome | outcome | P3.1 PASS |
| P3 target | neutral_band_delta_eur_mwh | Frozen boundary separating small spreads from directional outcomes | EUR/MWh | Development-wide Q25 parameter, fixed before holdout | frozen_parameter | P3.2 FROZEN at 5.9956075 |
| P3 target | target_label | UP, DOWN or NEUTRAL realized market-pressure class | text | Derived after delivery from spread and frozen delta | outcome | P3.3 PASS; missing spread remains missing label |
| Forecasts_Hour | HourUTC | Start of the forecast delivery hour in UTC | — | Delivery interval; canonical join time | decision_eligible (key) | Validated P1.1 |
| Forecasts_Hour | HourDK | Start of the forecast delivery hour in Danish local time | — | Delivery interval; DST interpretation only | decision_eligible (key) | Validated P1.1; not sole join key |
| Forecasts_Hour | PriceArea | Danish bidding zone | text | Static area selector | decision_eligible (key) | Validated P1.1; use DK1 |
| Forecasts_Hour | ForecastType | Forecasted production category: Solar, Offshore Wind or Onshore Wind | text | Static category selector | decision_eligible (key) | Validated P1.1 |
| Forecasts_Hour | ForecastDayAhead | Renewable-production forecast for the next day | MWh per hour | Generated at 17:50 and published at 18:00 Danish time according to official metadata | pending cutoff | Validated definition; outside primary H2 signal |
| Forecasts_Hour | ForecastIntraday | Renewable-production forecast for the coming day at 06:00 Danish time | MWh per hour | Intraday horizon; exact historical eligibility depends on delivery hour and cutoff | pending cutoff | Excluded from primary H2 pending further evidence |
| Forecasts_Hour | Forecast5Hour | Renewable-production forecast valid five hours ahead | MWh per hour | Fixed 5-hour horizon snapshot; exact minute timestamp is not stored | decision_eligible | P2.3: non-null value eligible at last-pre-delivery snapshot |
| Forecasts_Hour | Forecast1Hour | Renewable-production forecast valid one hour ahead | MWh per hour | Fixed 1-hour horizon snapshot; exact minute timestamp is not stored | decision_eligible | P2.3: non-null value eligible at last-pre-delivery snapshot |
| Forecasts_Hour | ForecastCurrent | Renewable-production forecast valid for the current delivery time | MWh per hour | Current-time forecast associated with TimestampUTC | diagnostic_only | Excluded from pre-delivery H2 signal |
| Forecasts_Hour | TimestampUTC | UTC generation timestamp for ForecastCurrent | — | Current-forecast generation time; not the 5h or 1h publication time | diagnostic_only | Validated P1.1 |
| Forecasts_Hour | TimestampDK | Danish-local generation timestamp for ForecastCurrent | — | Local equivalent of TimestampUTC | diagnostic_only | Validated P1.1; DST interpretation only |
| Elspotprices | HourUTC | Start of the price delivery hour in UTC | — | Delivery interval; canonical join time | decision_eligible (key) | Validated P1.2 |
| Elspotprices | HourDK | Start of the price delivery hour in Danish local time | — | Delivery interval; DST interpretation only | decision_eligible (key) | Validated P1.2; not sole join key |
| Elspotprices | PriceArea | Bidding zone for the area price | text | Static area selector | decision_eligible (key) | Validated P1.2; use DK1 |
| Elspotprices | SpotPriceDKK | Day-ahead spot price in the price area | DKK/MWh | Price for the delivery hour, formed in the preceding day-ahead market | decision_eligible (reference audit) | P2.3 timing passed; not selected for spread |
| Elspotprices | SpotPriceEUR | Day-ahead spot price in the price area | EUR/MWh | Price for the delivery hour, formed in the preceding day-ahead market | decision_eligible (reference) | P2.3 timing passed; selected as P_DayAhead,t |
| RegulatingBalancePowerdata | HourUTC | Start of the balancing delivery hour in UTC | — | Delivery interval; canonical outcome join time | outcome (key) | Validated P1.3 |
| RegulatingBalancePowerdata | HourDK | Start of the balancing delivery hour in Danish local time | — | Delivery interval; DST interpretation only | outcome (key) | Validated P1.3; not sole join key |
| RegulatingBalancePowerdata | PriceArea | Bidding zone for the balancing outcome | text | Static area selector | outcome (key) | Validated P1.3; use DK1 |
| RegulatingBalancePowerdata | ImbalancePriceEUR | Official imbalance price based on the dominating direction | EUR/MWh | Final price outcome for the delivery hour | outcome | Validated P1.3; selected as P_Balancing,t |
| RegulatingBalancePowerdata | BalancingPowerPriceUpEUR | Official upward balancing-power price component | EUR/MWh | Final directional price for the delivery hour | outcome (audit) | Validated P1.3; not independently selected as target |
| RegulatingBalancePowerdata | BalancingPowerPriceDownEUR | Official downward balancing-power price component | EUR/MWh | Final directional price for the delivery hour | outcome (audit) | Validated P1.3; not independently selected as target |
| RegulatingBalancePowerdata | ImbalanceMWh | Imbalance remaining after TSO activation of mFRR, aFRR and FCR | MWh | Ex-post physical-system diagnostic | outcome (diagnostic) | Validated P1.3; do not infer official direction from sign alone |
| RegulatingBalancePowerdata | mFRRUpActBal | Danish mFRR activation for upward balancing | MWh | Ex-post activation volume | outcome (diagnostic) | Validated definition P1.3 |
| RegulatingBalancePowerdata | mFRRDownActBal | Danish mFRR activation for downward balancing | MWh | Ex-post activation volume | outcome (diagnostic) | Validated definition P1.3 |
| ProductionConsumptionSettlement | GrossConsumptionMWh | Gross electricity consumption including grid losses and self-consumption | MWh | Settlement value for the completed delivery hour | diagnostic_only | Validated P1.4; H1-A demand component |
| ProductionConsumptionSettlement | OffshoreWindLt100MW_MWh + OffshoreWindGe100MW_MWh | Total actual offshore wind production across the two capacity bands | MWh | Settlement value for the completed delivery hour | diagnostic_only | Validated P1.4; summed without zero-filling |
| ProductionConsumptionSettlement | OnshoreWindLt50kW_MWh + OnshoreWindGe50kW_MWh | Total actual onshore wind production across the two capacity bands | MWh | Settlement value for the completed delivery hour | diagnostic_only | Validated P1.4; summed without zero-filling |
| ProductionConsumptionSettlement | SolarPowerLt10kW_MWh + SolarPowerGe10Lt40kW_MWh + SolarPowerGe40kW_MWh + SolarPowerSelfConMWh | Total actual solar production, including estimated self-consumption | MWh | Settlement value for the completed delivery hour | diagnostic_only | Validated P1.4; summed without zero-filling |
| ProductionConsumptionSettlement | ActualResidualLoadMWh (derived) | Gross consumption remaining after actual wind and solar | MWh | Ex-post derived value for the delivery hour | diagnostic_only | Validated P1.4; negative values preserved |
| ProductionConsumptionSettlement | ExchangeNO/SE/GE/NL/GB/GreatBelt_MWh | Actual settled exchange; negative is export and positive is import | MWh | Settlement value for the completed delivery hour | diagnostic_only | Validated P1.4; GB historical nulls preserved |
| Transmissionlines | ImportCapacity | Transfer capacity from connected area into DK1 | MWh | Capacity for the coming day, officially published before 10:00 | decision_eligible (conditional) | P2.3 timing passed; border subset remains P6.1 |
| Transmissionlines | ExportCapacity | Transfer capacity from DK1 to connected area | MWh | Capacity for the coming day, officially published before 10:00 | decision_eligible (conditional) | P2.3 timing passed; mixed source signs require P6.1 rule |
| Transmissionlines | ScheduledExchangeDayAhead | Planned cross-border exchange from day-ahead price calculation | MWh | Day-ahead schedule; negative export, positive import | decision_eligible (conditional) | P2.3 timing passed; GB values unavailable in legacy extract |
| Transmissionlines | ScheduledExchangeIntraday | Final stored intraday scheduled exchange | MWh | Final intraday aggregate without historical vintage | diagnostic_only | Validated P1.4; not a point-in-time snapshot |
| Transmissionlines | PhysicalExchangeNonvalidated | SCADA-based measured cross-border exchange | MWh per hour | Realized and nonvalidated delivery-hour value | diagnostic_only | Validated P1.4 |
| Transmissionlines | PhysicalExchangeSettlement | Settled measured cross-border exchange | MWh | Realized settlement value after delivery | diagnostic_only | Validated P1.4 |
| CountertradeIntraday | PublicationDate | Time when the source published the stored request version | — | Danish local publication time converted to UTC | decision_eligible (conditional key) | P2.3: require PublicationDate < delivery_start; 282 stored rows fail |
| CountertradeIntraday | VolumeUpMW | Net volume Energinet intended to buy in intraday | MW | Request version published before or around delivery | decision_eligible (conditional) | 7,469 stored rows pass cutoff; partial coverage and overwritten versions remain |
| CountertradeIntraday | VolumeDownMW | Net volume Energinet intended to sell in intraday | MW | Request version published before or around delivery | decision_eligible (conditional) | 7,469 stored rows pass cutoff; partial coverage and overwritten versions remain |
| PowerSystemRightNow | production / flow / activated aFRR fields | One-minute actual system state | mixed | Upscaled real-time SCADA values | diagnostic_only or lagged candidate | Registered P1.4; no same-hour final value in decision model |
| Realtime Electricity Market / mFRR Request | timeStamp, mtuStart, area, value | Current mFRR amount sent to the activation optimization function | MW | Published shortly before each current MTU; period endpoint limited to seven days | unavailable_for_development | Registered P1.4; cannot reconstruct 2022–2024 |
| MfrrReservesDK1 + mFRRCapacityMarket | demand / procured reserve / capacity price | mFRR capacity-market context | MW and EUR/MW | Legacy and successor daily procurement results | decision_eligible (conditional) | Registered P1.4; schema bridge and timing deferred to P6.1 |

## Point-in-Time Classes

- `decision_eligible`: available at the simulated decision time
- `diagnostic_only`: useful for explanation but unavailable for the decision
- `outcome`: known only after the delivery period

`decision_eligible (conditional)` now means timing may pass at the frozen
last-pre-delivery cutoff while a source-specific gate still remains. For
transmission that gate is P6.1 border/sign handling; for countertrade it is
partial coverage, overwritten versions and the row-level publication filter.

`external_candidate_pending_access_timing` and
`unavailable_for_development` are source-inventory statuses. They prevent an
unverified or out-of-period source from being silently promoted into the
model.

`decision_eligible (reference)` means the field is an already-established
pre-delivery benchmark used in the target definition and available at the
P2.3 last-pre-delivery cutoff.

## P2 Timestamp and Hourly-Base Contract

- Decision anchor: `decision_time_utc = delivery_start_utc`
- Availability rule: information must be available strictly before the anchor
- Interpretation: last pre-delivery information snapshot; no executable
  intraday trade or exact-minute vintage claim
- Canonical base key: `delivery_start_utc + price_area`
- Local-time fields: `delivery_start_local`, `local_wall_time`, `local_date`,
  `local_hour`, `utc_offset_minutes`, `is_dst`, `local_hour_occurrence`
- DST rule: repeated local hours remain separate UTC rows; `HourDK` is not a
  unique key
- Base-table size: 21,887 rows and 93 columns
- Local processed file: `data/processed/p2/hourly_base_development.parquet`
- P2 does not create spread, labels, delta or forecast-revision values
- Evidence: `research/evidence/p2_data_pipeline/`

## P3 Target Contract

- Formula: `balancing_spread_eur_mwh = imbalance_price_eur_mwh - spot_price_eur_mwh`
- Alignment: same DK1 `delivery_start_utc`, with both prices in EUR/MWh
- Frozen delta: `5.9956075 EUR/MWh`
- Delta population: 15,392 nonzero absolute development spreads; one missing
  spread and 6,494 observed-zero spreads excluded
- Quantile method: pandas linear interpolation, frozen before holdout access
- Labels: UP above `+delta`, DOWN below `-delta`, NEUTRAL between and including
  both boundaries; a missing spread has no label
- Development counts: 4,354 UP, 7,190 DOWN, 10,342 NEUTRAL and one missing
- Local processed file: `data/processed/p3/target_development.parquet`
- Target-table size: 21,887 rows and 99 columns
- Baselines: majority must be fit on training labels only; persistence remains
  an ex-post reference; hour-of-week training majority is registered as the
  availability-safe supplement
- Evidence: `research/evidence/p3_target_construction/`

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

## P1.4 Source and Eligibility Contract

- `ProductionConsumptionSettlement` is the selected H1-A actual-fundamentals
  source. Its 21,887 DK1 development hours are complete, but settlement delay
  and later revisions make all actual-derived fields diagnostic only.
- Actual wind sums two offshore and two onshore capacity bands. Actual solar
  sums three grid-production bands plus solar self-consumption. Residual load
  is gross consumption minus these two totals.
- Negative actual residual load is a possible physical state and remains in
  the data. It is not an error code or substitute for missingness.
- `Transmissionlines` provides hourly records for DE, DK2, GB, NL, NO2 and SE3
  across all development hours. Its official primary key is
  `HourUTC + PriceArea + ConnectedArea`.
- Import/export capacity and day-ahead scheduled exchange are conditional
  decision candidates. Exact cutoff mapping belongs to P2.3; border-specific
  availability, sign normalization and feature construction belong to P6.1.
- GB's legacy day-ahead fields are null in returned rows, and
  `ExportCapacity` contains mixed signs. Preserve both facts and define any
  later usable-border subset explicitly.
- Final intraday schedule and physical exchange are diagnostic only. The
  `ProductionConsumptionSettlement` exchange fields are the selected
  settlement-flow diagnostic; `ForeignExchange` is a registered alternative.
- Legacy `CountertradeIntraday` covers only part of development. Of 7,751
  final rows, 7,447 were published at least one hour before delivery, but the
  API overwrites earlier versions. It remains a conditional candidate and
  missing request days are not automatically zero.
- `CountertradeIntraday_v2` begins after development and is unavailable for
  this study period.
- No historical Energi Data Service day-ahead load forecast passed P1.4. The
  ENTSO-E day-ahead total-load forecast is registered for P5.2 as an external
  candidate pending access and publication-timing evidence.
- `PowerSystemRightNow` and `ElectricityBalanceNonv` are actual-state sources;
  only an explicitly lagged observation strictly before the cutoff could be
  reconsidered later. The separate live mFRR Request service retains at most
  seven days and is unavailable for 2022–2024. Reserve-capacity sources are
  registered conditional candidates outside the Level A requirement.

Complete evidence and the machine-readable inventory are under
`research/evidence/p1_4_sources/`.

## Registration Rules

- Do not classify a field as decision eligible only because it appears in historical data.
- Record the official definition, unit and timestamp meaning.
- Use `HourUTC` as the canonical join key unless source validation establishes otherwise.
- Retain Danish local time for interpretation and daylight-saving checks.
- Record missing values and duplicate keys explicitly.
- Do not convert missing values to zero without documented evidence.
- Do not access or register fields from the locked holdout before its formal unlock.
