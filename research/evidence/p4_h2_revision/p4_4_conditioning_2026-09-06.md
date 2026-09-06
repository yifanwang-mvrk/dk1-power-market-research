# P4.4 — H2 Conditioning and Failure Analysis

**Status:** complete — 2026-09-06
**Scope:** development only, exploratory / descriptive (E002)
**Holdout:** LOCKED AND UNUSED
**Declared before crossing outcomes:** meteorological seasons, hour blocks
[[0, 5, 'h00_05'], [6, 11, 'h06_11'], [12, 17, 'h12_17'], [18, 23, 'h18_23']], wind-level terciles, chronological split at
2024-01-01,
permutation seed 20260906.

## Conclusion

**CONDITIONALLY SUPPORTED — THE MECHANISM IS REAL (PERMUTATION P < 0.05) AND HOLDS ACROSS SEASON AND HOUR-OF-DAY, BUT IT FAILS AT WIND_LEVEL=LOW_WIND AND DOES NOT REPRODUCE ON THE 2024 H1 CHRONOLOGICAL HOLD-BACK**

## 1. Regime stratification — is the gradient everywhere?

Metric per cell: gradient Spearman (bucket index vs `P(DOWN) − P(UP)` share) and
the Q5−Q1 spread in `P(DOWN) − P(UP)`.

### By season
| Season | Hours | Gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
| autumn | 4,320 | +0.90 | +0.149 |
| spring | 6,484 | +1.00 | +0.217 |
| summer | 5,081 | +1.00 | +0.359 |
| winter | 5,729 | +0.90 | +0.115 |

### By hour-of-day block
| Block | Hours | Gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
| h00_05 | 5,389 | +1.00 | +0.173 |
| h06_11 | 5,389 | +1.00 | +0.207 |
| h12_17 | 5,419 | +1.00 | +0.249 |
| h18_23 | 5,417 | +1.00 | +0.137 |

### By expected wind level (5h forecast terciles)
| Level | Hours | Gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
| high_wind | 7,207 | +0.90 | +0.119 |
| low_wind | 7,210 | +0.30 | +0.047 |
| mid_wind | 7,197 | +1.00 | +0.288 |

Directionally consistent cells: ['season=autumn', 'season=spring', 'season=summer', 'season=winter', 'hour_block=h00_05', 'hour_block=h06_11', 'hour_block=h12_17', 'hour_block=h18_23', 'wind_level=high_wind', 'wind_level=mid_wind']
Flat or reversed cells: ['wind_level=low_wind']

## 2. Chronological development-only split

Train `< 2024-01-01` (17,408 h), validate
`>= 2024-01-01` (4,207 h; seasons
['spring', 'summer', 'winter'] only — the validate window is seasonally confounded).
Quintile edges, rule `c` and the hour-of-week baseline were refrozen on train.

- Validate gradient Spearman:
  `+0.10`,
  Q5−Q1 spread
  `+0.058`,
  directionally consistent: **False**
- Validate Spearman(revision, spread):
  `-0.0146`
- Rule vs baselines on validate (balanced accuracy / macro-F1):
  rule 0.354 /
  0.353;
  majority 0.333 /
  0.203;
  hour-of-week 0.333 /
  0.239;
  always-DOWN 0.333 /
  0.179
- Rule beats majority and hour-of-week on validate:
  **True**

## 3. Permutation null for the transparent rule

Shuffle `wind_revision` 500 times, re-score the rule.

- Observed balanced accuracy: `0.3647`
- Null mean `0.3334`, null p95 `0.3383`,
  null max `0.3426`
- p-value (null >= observed): `0.0000` ->
  rule uses information: **True**

## Chart

`p4_4_regime_gradient_chart_2026-09-06.png` — Q5−Q1 `P(DOWN) − P(UP)` spread by
regime; blue bars keep the predicted direction, red bars flatten or reverse.

## Limitations and carry-forward

- Development only, in-sample / descriptive; the chronological validate window
  covers only part of the year (['spring', 'summer', 'winter']), so its result is
  seasonally confounded and rests on 4,207 hours.
- Cross-border conditioning is H3 / P6; logistic regression and probability
  calibration are P10; the true out-of-sample test is the Level C holdout.
