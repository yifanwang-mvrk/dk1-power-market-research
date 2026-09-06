# R01 — DK1 Short-Term Balancing Pressure: First Research Round

**Project:** DK1 Short-Term Power Market Research
**Memo version:** 1.1 — 2026-09-06
**Status:** MVP v1 Complete. The locked holdout has been evaluated once and is closed.
**Author:** Yifan Wang

---

## 1. The question

> Do renewable forecast revisions and observable system fundamentals contain
> information about short-term balancing pressure in DK1, and under what
> conditions does that relationship break down?

DK1 (Western Denmark) is one bidding zone with a very high wind share. For each
hourly delivery period the outcome studied is the **balancing spread**:

`Spread_t = RegulatingBalancePowerdata.ImbalancePriceEUR_t − Elspotprices.SpotPriceEUR_t`   (EUR/MWh)

The day-ahead price is the already-cleared reference; the balancing price is the
ex-post outcome. `Spread > 0` means the delivery hour settled *above* the
day-ahead reference (upward pressure), `Spread < 0` below it. This is a
balancing-pressure proxy, **not an executable intraday P&L**.

## 2. Method — why the conclusions are defensible

- **Point-in-time integrity.** Every field is classified `decision_eligible`,
  `diagnostic_only` or `outcome`. The decision cutoff is the delivery-hour start;
  only information available strictly before it can enter a simulated decision.
  Settlement actuals (published 9–15 days later) are diagnostic; the balancing
  price is an outcome.
- **A frozen target.** The three-class labels and the neutral band
  `δ = 5.9956075 EUR/MWh` (the linear Q25 of the 15,392 nonzero absolute
  development spreads) were fixed in the research config **before any holdout
  access** and before any hypothesis was crossed with the outcome.
- **Pre-registration.** The primary H2 test — variable, expected direction,
  buckets, statistic, baselines and the pass/fail bar — was written down and
  committed before the revision variable touched any outcome. This collapses a
  large researcher-degrees-of-freedom space to one procedure.
- **A locked holdout.** 2024-07-01 to 2024-12-31 has never been requested,
  fetched, inspected or analysed. Every pipeline loader aborts unless the holdout
  stays locked. All development request boundaries end exclusive at local
  2024-07-01.
- **Mandatory naive baselines.** Every directional result is compared with a
  majority-class baseline and an hour-of-week training-majority baseline;
  persistence (`y_hat_t = y_(t-1)`) is reported as an ex-post reference because
  the legacy source does not document its publication delay.
- **Reproducible.** One script per phase, hash-checked inputs, committed JSON
  evidence and quality gates, 40 automated tests.

## 3. Data and target

| Layer | Source (Energi Data Service) | Role |
|---|---|---|
| Day-ahead reference | `Elspotprices.SpotPriceEUR` | reference — validated across all 21,887 development hours |
| Balancing outcome | `RegulatingBalancePowerdata.ImbalancePriceEUR` | outcome — one documented missing hour (`2022-10-30T00:00Z`), preserved |
| Renewable forecast | `Forecasts_Hour` 5h and 1h fixed horizons | decision-eligible after the P2.3 cutoff contract |
| Actual fundamentals | `ProductionConsumptionSettlement` | diagnostic only (settlement delay) |
| Cross-border | `Transmissionlines` day-ahead capacity / schedule | decision-eligible candidates |

Development period: **2022-01-01 to 2024-06-30**, 21,887 unique DK1 delivery
hours on a UTC spine with Danish local time retained for DST. Frozen label
counts: **4,354 UP, 7,190 DOWN, 10,342 NEUTRAL** and one missing. NEUTRAL (47%)
is the base-rate majority; DOWN (33%) is the larger directional class.

## 4. H2 — Renewable forecast revision (primary)

**Variable:** `wind_revision_t = (Offshore + Onshore) (Forecast1Hour −
Forecast5Hour)`, MWh, same delivery hour, non-null pairs only. Available for
21,615 of 21,887 hours. The wind forecast is revised in essentially every hour
(0 wind-aggregate hours with `5h == 1h` exactly), so the variable carries real
information.

**Mechanism:** a positive revision means more wind is expected as delivery
approaches → a looser expected balance → a higher probability the hour settles
DOWN.

**Round-1 result (pre-registered, in-sample):** **SUPPORTED — weak and
asymmetric.**

| signed `wind_revision` quintile | P(UP) | P(DOWN) |
|---|---:|---:|
| Q1 (most negative) | 24.7% | 27.3% |
| Q5 (most positive) | 17.2% | 38.7% |

`P(DOWN) − P(UP)` rises monotonically across all five buckets. The rank
association is real but small: Spearman(revision, signed spread) = −0.096, 95%
bootstrap CI [−0.109, −0.083]. A transparent threshold rule beats the
availability-safe baselines on balanced accuracy (0.365 vs 0.333 / 0.345) but
loses on plain accuracy and trails the ex-post persistence reference. Its skill
is one-sided: real on the DOWN side (2,032 correct vs 901 opposite), essentially
absent on the UP side (845 vs 907).

**Conditioning and failure analysis (P4.4):** **CONDITIONALLY SUPPORTED.**

- A permutation null (shuffle the revision 500 times) puts the rule's balanced
  accuracy above the null maximum — the weak edge is **not** chance (p ≈ 0).
- The gradient is robust across all four seasons and all four hour-of-day blocks
  (strongest in summer, weakest in winter).
- **Failure condition — low expected wind.** When the 5h wind forecast is in the
  bottom tercile the gradient collapses (gradient Spearman +0.30, Q5−Q1 spread
  +0.047 vs +0.288 for mid wind). When the system is already wind-poor, other
  factors dominate the balancing outcome.
- **It does not reproduce out-of-time.** Trained on 2022–2023 and validated on
  2024 H1 (4,207 hours), the gradient is essentially flat (Spearman +0.10,
  association −0.015). The window is small and seasonally confounded — a warning,
  and the reason the Level C holdout matters.

## 5. H1 — Residual load and system tightness

**Variable:** `residual_load = demand − wind − solar`. Higher residual load = a
tighter physical system = a higher probability of upward pressure.

**H1-A (diagnostic, actual residual load):** complete for all 21,887 hours,
5,974 with negative residual load (renewables exceeded demand), preserved. The
mechanism is **directionally present but weak and threshold-like** — `P(DOWN)`
holds near 35% through the lower residual-load quintiles then falls to 27% only
in the tightest quintile; Spearman(residual load, signed spread) = +0.057, CI
[+0.043, +0.070]. The effect concentrates exactly where H2 fails (wind-poor,
tight). **H1 and H2 are complementary, not redundant.**

**H1-B (decision-eligible proxy):** `residual_load_known = consumption
climatology − 5h renewable forecast`, where the climatology is a point-in-time
expanding same-(weekday, hour) mean lagged past the settlement delay. Available
for 21,184 hours; it tracks actual residual load at Spearman +0.92 and
reproduces the H1 direction, though its own spread association is as weak as
H1-A. Registered as an eligible P7 input, not a standalone signal. A stronger
H1-B needs the external ENTSO-E day-ahead load forecast (not yet accessed).

## 6. H3 — Cross-border and system conditions

**Question:** does the H2 relationship change with cross-border conditions?

Decision-eligible day-ahead import/export capacity and scheduled exchange (over
DE, DK2, NL, NO2, SE3; GB excluded, all day-ahead fields null) **do not
materially change the H2 gradient** — the gradient by tercile shows a
middle-highest hump, a noise signature. Interconnector capacity barely varies
hour to hour, so it cannot carry conditioning information.

Only the **realized** net-import flow (diagnostic, unknown at decision time)
shows a weak steepening — the wind-revision→DOWN gradient is +0.231 when DK1
ends up short vs +0.175 when long, consistent with a congested export direction
trapping a wind surplus.

**Conclusion: diagnostic conditioning only. No decision-eligible H3 signal.**

## 7. The transparent signal

A small decision table over decision-eligible inputs only. Each hypothesis
speaks only where it has evidence:

- **H2 → DOWN PRESSURE (MEDIUM)** when the wind revision is in the top 20% by
  magnitude and the 5h wind forecast is not in the low-wind blind spot. H2 never
  emits UP.
- **H1-B → UP PRESSURE (LOW)** when the known residual-load proxy is in the top
  20% (very tight). H1 never emits DOWN.
- **NO TRADE** on conflict, on silence, or on a missing input. No case supports
  High confidence.

**Result (development, in-sample):** an active view in 32.7% of hours.

| Signal | Hours | P(DOWN) realized | P(UP) realized |
|---|---:|---:|---:|
| DOWN PRESSURE | 2,936 | **40.0%** (base 32.9%) | 17.1% |
| UP PRESSURE | 4,218 | 28.5% | 21.2% (base 19.9%) |
| NO TRADE | 14,732 | 32.7% | 20.1% |

Balanced accuracy 0.347 vs majority 0.333 and hour-of-week 0.344 — a marginal
win; the signal loses on plain accuracy and is far below persistence.
MEDIUM-confidence views hit 0.40 (three-class) vs 0.21 for LOW, so the confidence
tiering is meaningful. The value is concentrated on the DOWN side.

## 8. Risk, invalidation and No Trade

Every active view carries the same **key risk**: hourly balancing outcomes are
dominated by shocks the eligible inputs cannot see (outages, demand surprises,
realized cross-border flows). **Invalidation** of a DOWN view: a low 5h wind
forecast (the blind spot), renewables arriving far from forecast, or the system
turning tight. **No Trade** is the correct output when H1 and H2 conflict, when
neither fires, or when an input is missing — roughly two thirds of hours.

## 9. The logistic model and the locked-holdout test

**Development (P10.1).** A multinomial logistic regression (`C = 1.0`,
`class_weight = balanced`) on ten decision-eligible features — the H2 revision,
the 5h wind level, a low-wind interaction, the solar revision, the H1-B proxy and
cyclical time — against the frozen labels, with a time-ordered
train / calibration / validation split and Platt calibration. The coefficient
signs matched the H1/H2 mechanisms on all five checked terms. On the 2024 H1
development validation slice it had no edge — the calibrated argmax collapsed to
the majority class — which was expected: 2024 H1 is exactly where the H2 gradient
failed to reproduce (§4).

**The one holdout evaluation (P10.3, owner-approved, 2026-09-06).** The
specification was frozen at a git commit, prior non-use of the holdout was
machine-verified, and the frozen model was evaluated **once** on
2024-07-01 to 2024-12-31 (4,331 scored hours). The holdout is now closed.

| Method | Balanced accuracy | Macro-F1 |
|---|---:|---:|
| Logistic (calibrated) | **0.352** | **0.297** |
| Majority (development) | 0.333 | 0.247 |
| Hour-of-week (development) | 0.329 | 0.280 |
| Persistence (ex-post reference) | 0.635 | 0.635 |
| P7 transparent rule | 0.348 | 0.349 |

- The calibrated model **beats both availability-safe baselines** on balanced
  accuracy and macro-F1 by about two points — real, but within the range that
  4,331 hours of sampling can produce.
- It predicts `NEUTRAL` for 95% of hours. On the 212 hours it calls `DOWN`, the
  outcome is `DOWN` 49% of the time versus a 27% base rate — the signal lives on
  the downward side, as everywhere upstream.
- **No probability skill:** multiclass Brier 0.593 versus a development-class-
  frequency reference of 0.582.
- Strongest in summer (balanced accuracy 0.362), below the majority baseline in
  winter (0.326) — consistent with the development conditioning.
- The primary Q25 specification stands (Q20 0.355, Q30 0.349).

## 10. Limitations

- The primary effect is weak (`|Spearman| ≈ 0.1` in development) and did not
  reproduce on the 2024 H1 development hold-back; the ~2-point holdout edge is
  within sampling range.
- Development descriptive results use a δ and buckets estimated on the whole
  development period; the holdout uses that fixed δ.
- The model has no demand-shock, outage or realized-flow information — hourly
  balancing outcomes are dominated by what the decision-eligible inputs cannot
  see.
- The round-1 rule-vs-baseline gate rewards attempting all three classes; a
  stricter test would require beating a directional baseline or a proper scoring
  rule.
- Cross-border conditioning (H3) is diagnostic only; no decision-eligible signal
  was found.
- **This is not a deployable or profitable signal, and no such claim is made.**
  Balancing pressure is a market-outcome proxy, not executable intraday P&L.

## 11. Bottom line

Renewable wind-forecast revisions carry a small amount of directionally correct
information about DK1 balancing pressure — concentrated on the downward side,
present mainly when wind is a material factor, and it **survived the
locked-holdout test only marginally**: the frozen model edges the
availability-safe baselines by about two points on balanced accuracy, with no
probability skill and far below the ex-post persistence reference. Residual load
adds a weak, complementary tight-system signal exactly where the wind revision
fails. Day-ahead cross-border capacity adds nothing usable.

The mechanism is real and it did not vanish out of sample, but it is not an edge
worth acting on. The MVP is complete on that finding — the value of the project
is the point-in-time discipline, the pre-registration, the untouched-until-once
holdout, and reporting the result exactly as it came out.

## 12. What a next round would change

- A stricter evaluation: a proper multiclass scoring rule, a directional baseline
  to beat, and repeated time-blocked cross-validation rather than one split.
- The ENTSO-E day-ahead load forecast to replace the interim H1-B climatology
  proxy (external access pending).
- Border-level cross-border flow modelling and countertrade features for a real
  H3 test.
- Only after fresh, later, unseen data — anything informed by this holdout is
  now exploratory.
