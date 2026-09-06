# P1.2 Elspotprices Development Validation

**Status:** PASS
**Day-ahead reference feasibility:** FEASIBLE FOR THE DECLARED DEVELOPMENT PERIOD

## Business conclusion

The legacy Energinet `Elspotprices` dataset provides a complete, unique hourly DK1 day-ahead reference for the declared development period. `SpotPriceEUR` is selected as `P_DayAhead,t` because it is the official area price in the frozen target unit, EUR/MWh.

## Official data contract

- Dataset: `Elspotprices` (ID `30`)
- Title: Elspot Prices (Discontinued – see description)
- Author: Energinet
- Resolution: `1 hour (PT1H)`
- Official primary key: `HourUTC, PriceArea`
- Tags: `Discontinued, Hour, Price Area`
- `SpotPriceEUR`: day-ahead spot price in the price area, `EUR per MWh`
- `SpotPriceDKK`: day-ahead spot price in the price area, `DKK per MWh`
- Official market meaning: the day-ahead price indicates the balance between supply and demand for delivery the following day.

## Scope and holdout control

- Local development boundary: `2022-01-01` to `2024-06-30`
- Expected delivery hours: `21887`
- API-reported total: `21887`
- Returned records: `21887`
- Distinct delivery hours: `21887`
- First local hour: `2022-01-01T00:00:00+01:00`
- Last local hour: `2024-06-30T23:00:00+02:00`
- Missing delivery hours: `0`
- Extra delivery hours: `0`
- Records at or after holdout start: `0`

## Key and price quality

- Duplicate primary-key rows: `0`
- Maximum rows per primary key: `1`
- HourDK rows inconsistent with HourUTC conversion: `0`

| Field | Unit | Null | Zero | Negative | Minimum | Maximum | Median |
|---|---|---:|---:|---:|---:|---:|---:|
| SpotPriceDKK | DKK per MWh | 0 | 76 | 503 | -3277.39 | 6478.24 | 745.93 |
| SpotPriceEUR | EUR per MWh | 0 | 76 | 503 | -440.1 | 871 | 100.1 |

## DST evidence

- `2022-03-27`: expected `23`, rows `23`, unique HourUTC `23`, unique HourDK `23`.
- `2022-10-30`: expected `25`, rows `25`, unique HourUTC `25`, unique HourDK `24`.
- `2023-03-26`: expected `23`, rows `23`, unique HourUTC `23`, unique HourDK `23`.
- `2023-10-29`: expected `25`, rows `25`, unique HourUTC `25`, unique HourDK `24`.
- `2024-03-31`: expected `23`, rows `23`, unique HourUTC `23`, unique HourDK `23`.

## Selected reference field

- Field: `SpotPriceEUR`
- Unit: `EUR per MWh`
- Target role: `P_DayAhead,t in Spread_t = P_Balancing,t - P_DayAhead,t`
- PIT class: `decision_eligible (reference)`
- Reason: It is the official DK1 day-ahead area price and matches the project's frozen EUR/MWh target unit.

## Frozen P1.2 handling rules

- Filter PriceArea to DK1.
- Use HourUTC and PriceArea as the canonical primary key.
- Use HourDK for interpretation and DST checks, not as the sole join key.
- Use SpotPriceEUR as P_DayAhead,t in EUR/MWh.
- Retain SpotPriceDKK as an audit field but do not mix currencies in the spread.
- Preserve zero and negative day-ahead prices as valid market observations.
- Do not impute missing price rows or null prices as zero.
- Treat the price as a pre-delivery reference, not as the realized balancing outcome.
- Lock the exact simulated decision cutoff and availability mapping in P2.3.
- Use the successor DayAheadPrices dataset for any extension after 2025-09-30.
- Respect API rate limits and Retry-After headers in the P2 client.

## Open limitations carried forward

- The legacy Elspotprices dataset is discontinued after 2025-09-30, outside the declared development and holdout periods.
- The dataset stores delivery-hour prices but no row-level publication timestamp.
- Any future extension across the 2025 market-time-unit change requires a separately validated migration to DayAheadPrices.
