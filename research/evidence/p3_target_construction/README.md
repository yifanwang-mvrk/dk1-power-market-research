# P3 Target Construction Evidence

**Status:** PASS — P3.1 through P3.4 completed on 2026-09-06
**Holdout:** LOCKED AND UNUSED

## Frozen target

`balancing_spread_eur_mwh = imbalance_price_eur_mwh - spot_price_eur_mwh`

- Same DK1 delivery hour and EUR/MWh unit on both sides
- Valid spreads: `21,886`
- Missing spreads: `1`
- Preserved missing outcome: `2022-10-30T00:00:00+00:00`

## Frozen neutral band

- Rule: Q25 of nonzero absolute development spreads
- Eligible observations: `15,392`
- Excluded observed-zero spreads: `6,494`
- Method: linear interpolation
- Frozen delta: `5.9956075 EUR/MWh`

## Development labels

| Label | Count | Share of valid labels |
|---|---:|---:|
| UP | 4,354 | 19.89% |
| DOWN | 7,190 | 32.85% |
| NEUTRAL | 10,342 | 47.25% |

The single missing spread has no label. Observed zero spreads and both exact
boundaries belong to NEUTRAL. No missing value is converted to zero.

## Baselines

- Development-wide descriptive majority: `NEUTRAL`
- Majority descriptive accuracy: `47.25%`
- Ex-post persistence eligible pairs: `21,884`
- Ex-post persistence descriptive accuracy: `71.45%`
- Persistence remains an ex-post reference because the historical publication
  delay of the preceding balancing outcome is undocumented.
- An availability-safe hour-of-week training-majority reference is registered
  before evaluation. It must be fit independently inside each future training
  segment.

These are in-sample descriptive facts, not evidence of a predictive edge or
executable trading performance.

## Quality gate

- Target rows: `21,887`
- Target columns: `99`
- Critical checks passed: `13/13`
- Holdout rows: `0`
