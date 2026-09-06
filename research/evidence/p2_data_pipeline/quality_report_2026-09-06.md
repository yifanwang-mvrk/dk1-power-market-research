# P2 Development Data Quality Report

**Status:** PASS
**Holdout:** LOCKED AND UNUSED

## Structural result

- Expected DK1 delivery hours: `21,887`
- Hourly base rows: `21,887`
- Duplicate UTC rows: `0`
- Holdout rows: `0`
- First UTC delivery hour: `2021-12-31T23:00:00+00:00`
- Last UTC delivery hour: `2024-06-30T21:00:00+00:00`

## Core coverage

- Spot price missing hours: `0`
- Imbalance price missing hours: `1`
- Preserved balancing gap: `2022-10-30T00:00:00+00:00`
- Actual gross-consumption missing hours: `0`
- Countertrade stored rows joined: `7,751`
- Countertrade rows published before cutoff: `7,469`

| Forecast type | Valid same-hour 5h/1h pairs |
|---|---:|
| Offshore Wind | 21,667 |
| Onshore Wind | 21,637 |
| Solar | 21,664 |

## Quality decisions

- UTC is the unique join key; Danish local time is retained for interpretation.
- Both occurrences of a repeated DST local hour remain separate rows.
- Missing source rows and null values remain missing; observed zeros remain zero.
- Outcome and diagnostic columns are present for later research but are excluded from decision-time eligibility.
- P2 does not compute spread, labels or forecast revisions.
- No holdout row was requested, processed or inspected.
