# P10.3 — Locked-Holdout Evaluation

**Status:** COMPLETE — 2026-09-06 — one owner-approved evaluation (D036)
**Holdout window:** 2024-07-01 .. 2025-01-01 (exclusive)
**Holdout:** EVALUATED ONCE. Config re-locked as `state: evaluated`.

## Conclusion

**On the locked 2024 H2 holdout (4,331 scored hours) the frozen calibrated logistic reaches balanced accuracy 0.352 vs majority 0.333 and hour-of-week 0.329. It beats both availability-safe baselines. Multiclass Brier 0.593 vs the development-class-frequency reference 0.582 (not better). The primary Q25 result stands as reported.**

## Coverage

4,417 holdout hours; 4,417 with a valid
label; 4,331 scored (feature-complete and
labelled); 0 hours missing a balancing price.
Holdout label counts: {'UP': 645, 'DOWN': 1170, 'NEUTRAL': 2602}.

Model refit: development < 2024-01-01; Platt calibration on [2024-01-01, 2024-07-01); C=1.0 as selected in P10.1 (16,883 fit
rows, 4,207 calibration rows).

## Primary metrics (holdout)

| Method | Balanced acc. | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| Logistic (calibrated) | 0.352 | 0.297 | 0.593 |
| Logistic (raw) | 0.383 | 0.289 | 0.280 |
| Majority (development) | 0.333 | 0.247 | 0.590 |
| Hour-of-week (development) | 0.329 | 0.280 | 0.553 |
| Persistence (ex-post) | 0.635 | 0.635 | 0.699 |
| P7 transparent rule | 0.348 | 0.349 | 0.471 |

Multiclass Brier (calibrated): 0.5929
vs development-class-frequency reference
0.5815.

## Calibrated prediction distribution (holdout)

| Predicted | n | realized UP | realized DOWN | realized NEUTRAL |
|---|---:|---:|---:|---:|
| UP | 0 | — | — | — |
| DOWN | 212 | 7.5% | 49.1% | 43.4% |
| NEUTRAL | 4,119 | 15.0% | 25.2% | 59.8% |

## By season and wind level

See `p10_3_holdout_result_2026-09-06.json` `by_season` and `by_wind_level`.

## Delta sensitivity (secondary, pre-declared)

| Delta | Value | Calibrated balanced acc. | Majority balanced acc. |
|---|---:|---:|---:|
| Q20 | 3.1700 | 0.355 | 0.333 |
| Q25_primary | 5.9956 | 0.352 | 0.333 |
| Q30 | 8.6530 | 0.349 | 0.333 |

## Protocol

Any change informed by this holdout is exploratory and needs fresh unseen data.
