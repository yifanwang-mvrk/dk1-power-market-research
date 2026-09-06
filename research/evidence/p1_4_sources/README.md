# P1.4 Fundamentals, Cross-Border and System-Source Evidence

This directory preserves the evidence used to complete the P1.4 source and
point-in-time eligibility inventory. Completion means that every required
research role has a selected source, a conditional candidate, or an evidenced
unavailable status. It does not mean that every historical field is suitable
for a decision model.

## Preserved evidence

- Official Energi Data Service metadata for
  `ProductionConsumptionSettlement`, `Transmissionlines`, `ForeignExchange`,
  `CountertradeIntraday`, its 2025 successor, `ElectricityBalanceNonv`,
  `PowerSystemRightNow`, `MfrrReservesDK1` and `mFRRCapacityMarket`.
- The official dataset catalogue captured on 2026-09-06.
- Reviewable development-period samples for actual fundamentals,
  transmission lines and countertrade.
- `development_extract_manifest_2026-09-06.json`, which records the three
  ignored raw extracts, exact bounded request URLs, sizes and SHA-256 hashes.
- `development_validation_2026-09-06.json` and `.md`, produced by
  `src/validate_p1_4_sources.py`.
- `source_eligibility_inventory_2026-09-06.json`, the machine-readable source
  decision for H1 and H3.

## Decisions established

### Actual fundamentals

Use `ProductionConsumptionSettlement` to construct historical actual wind,
actual solar and actual residual load. Its 21,887 DK1 development hours are
complete. Because the dataset is settlement data updated after delivery and
subject to later revisions, these variables are `diagnostic_only`.

`ActualResidualLoadMWh = GrossConsumptionMWh - ActualWindMWh - ActualSolarMWh`

Actual wind sums the two offshore and two onshore fields. Actual solar sums the
three grid-production bands and solar self-consumption. Negative residual load
is physically possible and is preserved. It means the selected renewable
production total exceeded gross consumption in that hour; it is not treated as
a missing-value code.

### Cross-border conditions

The discontinued hourly `Transmissionlines` dataset covers every development
hour and six DK1 connections: DE, DK2, GB, NL, NO2 and SE3. Its official
metadata says capacities for the coming day are published before 10:00 and
that day-ahead scheduled exchange results from the spot-market calculation.
Therefore `ImportCapacity`, `ExportCapacity` and
`ScheduledExchangeDayAhead` are pre-delivery candidates. P2.3 must still map
them to the project's exact decision cutoff, and P6.1 must define
border-specific handling.

The conditions are material: `ExportCapacity` contains both signs and the
metadata does not specify a sign validation rule; GB's legacy day-ahead
capacity and schedule fields are null in all returned GB rows. Values and nulls
are preserved. Final intraday schedules and physical exchanges are
`diagnostic_only` because the extract does not retain historical intraday
versions and physical flows are realized outcomes.

Energinet's discontinuation notice registers ENTSO-E scheduled commercial
exchange and implicit day-ahead allocations, plus JAO flow-based capacity, as
successor sources for future extensions. They are registered candidates rather
than silently mixed into the declared historical development extract.

### Countertrade and system context

Legacy `CountertradeIntraday` begins during the development period on
2023-04-18. It includes publication time and a version number, but later source
updates overwrite earlier versions. Of 7,751 returned final rows, 7,447 have a
publication time at least one hour before delivery. The source is therefore a
partial-period `conditional_decision_candidate`; P2.3 must enforce the final
cutoff, and no absent request day may be invented as zero. The v2 successor
starts in 2025 and is unavailable for this development period.

`PowerSystemRightNow` and `ElectricityBalanceNonv` are actual/SCADA sources.
They are diagnostic unless a value strictly observed before the decision
cutoff is deliberately lagged. `MfrrReservesDK1` and `mFRRCapacityMarket`
register the legacy/successor reserve-capacity context. Their pre-delivery
auction nature makes them candidates, while their schema bridge and exact
availability remain P6.1 work outside the Level A requirement.

Energinet's separate live mFRR Request service retains only a seven-day period
window. It cannot reconstruct 2022–2024 and is explicitly unavailable for the
development backtest.

No validated historical Energi Data Service day-ahead load forecast was found.
The ENTSO-E day-ahead total-load forecast is registered as an external H1-B
candidate pending access and timing evidence in P5.2.

## Scope control

All full extracts stop at local 2024-07-01 00:00, the exclusive end of the
development boundary. No locked-holdout row was requested or inspected.
Missing values remain missing, and the project still makes no executable
trading P&L claim.

Official entry points:

- <https://api.energidataservice.dk/meta/Dataset/ProductionConsumptionSettlement>
- <https://api.energidataservice.dk/meta/Dataset/Transmissionlines>
- <https://api.energidataservice.dk/meta/Dataset/CountertradeIntraday>
- <https://api.energidataservice.dk/meta/Dataset/PowerSystemRightNow>
- <https://transparency.entsoe.eu/>
- <https://www.jao.eu/>
