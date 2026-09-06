# Forecasts_Hour One-Day Sample Profile

## Scope

- Source file: `research/evidence/p1_1_forecasts_hour/sample_dk1_2024-04-05_2024-04-06.json`
- UTC coverage: `2024-04-05T00:00:00` to `2024-04-05T23:00:00`
- Records: `72`
- Distinct delivery hours: `24`

## Row Grain and Key

- Official primary key: `HourUTC, PriceArea, ForecastType`
- Unique keys: `72`
- Rows involved in duplicate keys: `0`

## Forecast Types and Pairing

| Forecast type | Rows | 5h and 1h non-null | Both positive | 5h or 1h zero |
|---|---:|---:|---:|---:|
| Offshore Wind | 24 | 24 | 24 | 0 |
| Onshore Wind | 24 | 24 | 24 | 0 |
| Solar | 24 | 24 | 16 | 8 |

## Interpretation Limits

- A non-null or positive value does not prove point-in-time eligibility.
- TimestampUTC describes ForecastCurrent, not Forecast1Hour or Forecast5Hour.
- A one-day sample cannot establish development-period coverage.
- Zero and missing must not be treated as equivalent without evidence.
