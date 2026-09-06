# P1.1 Forecasts_Hour Development Validation

**Status:** CONDITIONAL PASS
**H2 5h-to-1h feasibility:** FEASIBLE WITH DOCUMENTED CONDITIONS

## Business conclusion

The dataset supports same-hour DK1 5h-to-1h renewable forecast-revision research with explicit missingness, zero-value, DST and publication-timing conditions. It does not support a claim of complete tick-by-tick forecast-vintage reconstruction.

## Official data contract

- Dataset: `Forecasts_Hour` (ID `40`)
- Title: Forecast Wind and Solar Power, Hour Resolution
- Author: Energinet
- Active: `True`
- Resolution: `1 hour (PT1H)`
- Source update frequency: `PT5M`
- Official primary key: `HourUTC, PriceArea, ForecastType`
- Forecast unit: `MWh per hour`

## Scope and holdout control

- Local development boundary: `2022-01-01` to `2024-06-30`
- Expected delivery hours: `21887`
- Returned records: `65499`
- First local hour: `2022-01-01T00:00:00+01:00`
- Last local hour: `2024-06-30T23:00:00+02:00`
- Records at or after holdout start: `0`

## Coverage and revision pairing

| Forecast type | Rows | Whole-row missing hours | Row coverage | 5h/1h non-null pairs | Pair coverage vs expected | Both positive | 5h or 1h zero |
|---|---:|---:|---:|---:|---:|---:|---:|
| Offshore Wind | 21830 | 57 | 99.7396% | 21667 | 98.9948% | 21619 | 48 |
| Onshore Wind | 21830 | 57 | 99.7396% | 21637 | 98.8578% | 21618 | 0 |
| Solar | 21839 | 48 | 99.7807% | 21664 | 98.9811% | 14837 | 6854 |

## Whole-row missing intervals

### Offshore Wind

- `2024-04-13T00:00:00+02:00` to `2024-04-15T08:00:00+02:00`: 57 hours

### Onshore Wind

- `2024-04-13T00:00:00+02:00` to `2024-04-15T08:00:00+02:00`: 57 hours

### Solar

- `2024-04-13T00:00:00+02:00` to `2024-04-14T23:00:00+02:00`: 48 hours

## Null, zero and negative observations

| Forecast type | 5h null | 1h null | 5h zero | 1h zero | 5h negative | 1h negative |
|---|---:|---:|---:|---:|---:|---:|
| Offshore Wind | 103 | 109 | 11 | 42 | 0 | 0 |
| Onshore Wind | 119 | 127 | 0 | 0 | 11 | 8 |
| Solar | 110 | 118 | 6025 | 4615 | 0 | 0 |

## DST evidence

- `2022-03-27` expected `23` local delivery intervals.
  - Offshore Wind: `23` rows, `23` unique HourUTC, `23` unique HourDK.
  - Onshore Wind: `23` rows, `23` unique HourUTC, `23` unique HourDK.
  - Solar: `23` rows, `23` unique HourUTC, `23` unique HourDK.
- `2022-10-30` expected `25` local delivery intervals.
  - Offshore Wind: `25` rows, `25` unique HourUTC, `24` unique HourDK.
  - Onshore Wind: `25` rows, `25` unique HourUTC, `24` unique HourDK.
  - Solar: `25` rows, `25` unique HourUTC, `24` unique HourDK.
- `2023-03-26` expected `23` local delivery intervals.
  - Offshore Wind: `23` rows, `23` unique HourUTC, `23` unique HourDK.
  - Onshore Wind: `23` rows, `23` unique HourUTC, `23` unique HourDK.
  - Solar: `23` rows, `23` unique HourUTC, `23` unique HourDK.
- `2023-10-29` expected `25` local delivery intervals.
  - Offshore Wind: `25` rows, `25` unique HourUTC, `24` unique HourDK.
  - Onshore Wind: `25` rows, `25` unique HourUTC, `24` unique HourDK.
  - Solar: `25` rows, `25` unique HourUTC, `24` unique HourDK.
- `2024-03-31` expected `23` local delivery intervals.
  - Offshore Wind: `23` rows, `23` unique HourUTC, `23` unique HourDK.
  - Onshore Wind: `23` rows, `23` unique HourUTC, `23` unique HourDK.
  - Solar: `23` rows, `23` unique HourUTC, `23` unique HourDK.

## Version and timestamp finding

- TimestampUTC in primary key: `False`
- Maximum rows per primary key: `1`
- Finding: The extract retains one row per delivery hour, area and forecast type. It does not contain row-level tick-by-tick publication history.
- `TimestampUTC` is the generation timestamp for `ForecastCurrent`; it is not the publication timestamp for `Forecast5Hour` or `Forecast1Hour`.

## Frozen P1.1 handling rules

- Join and deduplicate with HourUTC, PriceArea and ForecastType.
- Use HourDK for interpretation and DST checks, not as the sole join key.
- Compute 5h-to-1h revision only when both horizon values are non-null in the same primary-key row.
- Do not create rows for absent hours and do not impute absent or null forecasts as zero.
- Preserve observed zero and negative values and attach quality flags; do not silently coerce them.
- For Solar, report a sensitivity view restricted to pairs where both horizon values are positive.
- Treat Forecast5Hour and Forecast1Hour as fixed-horizon snapshots, not complete forecast-vintage history.
- Exclude ForecastCurrent and TimestampUTC from the pre-delivery H2 signal.
- Keep ForecastIntraday outside the primary H2 signal until its historical availability is separately evidenced.
- Lock the exact simulated decision cutoff in P2.3 before signal evaluation.

## Open limitations carried forward

- Exact minute-level publication timestamps for Forecast5Hour and Forecast1Hour are not stored in the dataset.
- The official >0 validation rule conflicts with observed zeros and a small number of negative wind forecasts.
- Thor offshore wind farm data is excluded by the official source.
- Known April 2024 missing data is confirmed, with type-specific observed gap lengths.
