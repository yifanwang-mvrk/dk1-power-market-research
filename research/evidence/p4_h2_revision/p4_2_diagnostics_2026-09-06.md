# P4.2 Revision Build and Diagnostics

**Status:** PASS — built on the frozen P2 hourly base on 2026-09-06
**Scope:** decision-eligible revision variables only; no outcome joined
**Holdout:** LOCKED AND UNUSED

## Coverage

| Series | Available pairs | Dropped (missing horizon) |
|---|---:|---:|
| Offshore wind | 21,667 | 220 |
| Onshore wind | 21,637 | 250 |
| Solar | 21,664 | 223 |
| **Wind aggregate (primary)** | **21,615** | **272** |

## Did the forecast actually change? (P4.1 R1 diagnostic)

- Wind aggregate hours where neither offshore nor onshore forecast moved
  (`5h == 1h` exact): 0
  (0.00% of available)
- Wind `abs(revision) <= 1 MWh`: 137
  (0.63%)
- Wind `abs(revision) <= 5 MWh`: 643
  (2.97%)
- Solar hours where `5h == 1h` exact:
  4,676
  (21.58%)

## Solar sample split (D021)

- All numeric pairs: 21,664
- Both horizons positive (daytime subset): 14,837
- Zero or non-positive daylight rows: 6,827

## Frozen wind_revision buckets (signed, development only)

Interior quintile edges (MWh): -101.100, -27.250, +42.125, +163.683
Tie handling: edges strictly increasing

| Quintile bucket | Size |
|---|---:|
| 1 (most negative revision) | 4,323 |
| 2 | 4,323 |
| 3 (middle) | 4,323 |
| 4 | 4,323 |
| 5 (most positive revision) | 4,323 |

Transparent-rule threshold `c` = Q60 of `abs(wind_revision)` =
`128.083 MWh` (frozen; the rule predicts DOWN if revision > c, UP if < -c).

Normalization floor for `wind_forecast_5h` (Q10 of positive values):
`276.575 MWh`.

## What P4.2 does not do

No outcome column is joined and no revision-outcome statistic is computed. The
contingency table, association and transparent-rule scoring are P4.3.
