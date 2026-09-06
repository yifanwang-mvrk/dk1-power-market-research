# P1.3 RegulatingBalancePowerdata Development Validation

**Validation status:** CONDITIONAL PASS
**Feasibility:** FEASIBLE WITH ONE DOCUMENTED MISSING DELIVERY HOUR
**Holdout status:** Locked and unused

## Conclusion

For the declared hourly development period, DK1 `RegulatingBalancePowerdata.ImbalancePriceEUR` is selected as `P_Balancing,t` in EUR/MWh. It is the official unified imbalance-price outcome for the delivery hour and is classified as `outcome`, not as information available at the simulated decision time. One complete delivery-hour row is absent from the official historical API response, so P1.3 receives a conditional pass.

## Source contract

- Dataset: `RegulatingBalancePowerdata` (ID `122`)
- Resolution: `1 hour (PT1H)`
- Official primary key: `HourUTC, PriceArea`
- Selected field: `ImbalancePriceEUR`
- Selected unit: `EUR per MWh`
- Target role: `P_Balancing,t` in `Spread_t = P_Balancing,t - P_DayAhead,t`
- Canonical join key: `HourUTC + PriceArea`
- Point-in-time class: `outcome`

The official field definition states that the imbalance price is based on the dominating direction: Up uses the maximum of the aFRR component or mFRR price, None uses the value of avoided activation / spot price, and Down uses the minimum of the aFRR component or mFRR price.

## Historical applicability

The Nordic single-price and single-position model went live on 2021-11-01, before the development period begins. Official Nordic Balancing Model evidence: <https://nordicbalancingmodel.net/confirmation-of-go-live-of-single-price-and-single-position-on-1-november-2021/>.

The active successor `ImbalancePrice` starts at `2025-03-04T12:15:00` with `15 minutes (PT15M)` resolution. It does not cover the declared 2022-2024 development period, so it is not substituted into this hourly historical extract.

## Development coverage

| Expected hours | Returned rows | Distinct hours | Coverage | Missing | Duplicate-key rows | Extra | Holdout |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 21,887 | 21,886 | 21,886 | 99.995431% | 1 | 0 | 0 | 0 |

Missing hour: `2022-10-30T00:00:00+00:00` / `2022-10-30T02:00:00+02:00`. A separate bounded API request returned five of six requested consecutive UTC hours and confirmed the same source gap.

## Price completeness and values

| Field | Null | Zero | Negative | Minimum | Median | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| `ImbalancePriceEUR` | 0 | 198 | 970 | -2200.0 | 94.491539 | 4704.43 |
| `BalancingPowerPriceUpEUR` | 0 | 59 | 334 | -129.960007 | 105.5 | 4704.43 |
| `BalancingPowerPriceDownEUR` | 0 | 221 | 1137 | -2200.0 | 88.669998 | 871.0 |

Zero, negative and extreme values are retained as market observations. They are not interpreted as missing solely because of their magnitude or sign.

## Unified-price relationship

| Relationship | Hours |
|---|---:|
| Matches Up only | 5,290 |
| Matches Down only | 7,900 |
| Matches both | 8,696 |
| Matches neither | 0 |

All returned `ImbalancePriceEUR` values match at least one official directional price. The unified field is therefore used directly; the project will not select Up or Down after observing which one produces a preferred result.

## DST checks

| Local date | Expected | Rows | Unique UTC | Unique HourDK |
|---|---:|---:|---:|---:|
| 2022-03-27 | 23 | 23 | 23 | 23 |
| 2022-10-30 | 25 | 24 | 24 | 24 |
| 2023-03-26 | 23 | 23 | 23 | 23 |
| 2023-10-29 | 25 | 25 | 25 | 24 |
| 2024-03-31 | 23 | 23 | 23 | 23 |

The 2022 fall-back day contains 24 rather than the expected 25 UTC hours because the first repeated local 02:00 hour is absent. The 2023 fall-back day retains 25 UTC hours even though only 24 local clock labels are unique. This confirms that `HourUTC` must remain the canonical time key.

## Availability and limitations

- `ImbalancePriceEUR` is an ex-post delivery outcome. It must never enter the decision-time feature set.
- The discontinued dataset reports update frequency as N/A and does not document an exact historical publication delay. That unresolved lag remains under I03/P2.3, including the feasibility of a persistence baseline based on the previous outcome.
- `ImbalanceMWh` is defined after TSO activations and is not used to recreate the official dominating direction.
- The source caution concerns missing DKK values for Up and Down regulation prices. The selected EUR target has no null values among returned rows.
- This balancing-pressure outcome is not an executable trading price or P&L claim.

## Handling rule for P2

Join to the day-ahead reference on `HourUTC + PriceArea`. Preserve the absent 2022-10-30 00:00 UTC outcome as missing and exclude it from calculations requiring a complete spread. Do not create or zero-fill the row.
