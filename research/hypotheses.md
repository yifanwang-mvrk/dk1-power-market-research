# Hypothesis Registry

**Project:** DK1 Short-Term Power Market Research
**Status:** H2 round-1 complete (supported, weak — P4.3); H1 and H3 sources
registered, testing not started
**Last updated:** 2026-09-06

## H1 — Residual Load and System Tightness

**Status:** P5 complete 2026-09-06 — H1-A (diagnostic): directionally present but
weak and threshold-like, concentrated in the tightest ~40% of hours. H1-B: a
decision-eligible climatology proxy is feasible (tracks actual residual load,
Spearman +0.92) but its own spread association is as weak as H1-A; registered as
an eligible P7 input, not a standalone signal. A proper H1-B still needs the
external ENTSO-E day-ahead load forecast (I06).
**Role:** Fundamental baseline hypothesis

### Question

Does higher residual load increase the probability of upward balancing pressure in DK1?

### Mechanism

Residual load represents demand remaining after wind and solar generation are deducted. Higher residual load may require more flexible conventional supply and may therefore be associated with tighter system conditions.

### Point-in-Time Constraint

Actual demand and actual renewable production may explain past outcomes but cannot be used as decision inputs unless equivalent forecasts were available at the simulated decision time.

P1.4 selected `ProductionConsumptionSettlement` for H1-A. Actual residual load
is gross consumption minus summed actual wind and actual solar. It is
`diagnostic_only` because settlement data arrive after delivery and can be
revised. The full development period contains 21,887 complete derived rows.

No validated historical Energi Data Service load-forecast source was found for
H1-B. The ENTSO-E day-ahead total-load forecast is registered as an external
candidate pending access and publication-timing evidence in P5.2.

### P5.1 — H1-A Mechanism Research (diagnostic)

**Run:** 2026-09-06, in-sample / descriptive (E002). Evidence:
`research/evidence/p5_h1_residual_load/p5_1_h1a_mechanism_2026-09-06.json`,
`p5_1_residual_load_label_chart_2026-09-06.png`. `residual_load_actual_mwh` is
`diagnostic_only` (D024) and complete for all 21,887 hours; 5,974 negative-value
hours are preserved.

`P(label | signed actual-residual-load quintile)`:

| Bucket | P(UP) | P(NEUTRAL) | P(DOWN) | UP−DOWN share |
|---|---:|---:|---:|---:|
| Q1 (highest renewables) | 18.4% | 47.1% | 34.6% | −0.162 |
| Q2 | 19.1% | 46.0% | 34.9% | −0.158 |
| Q3 | 19.6% | 44.5% | 35.9% | −0.163 |
| Q4 | 19.9% | 48.4% | 31.6% | −0.117 |
| Q5 (tightest) | 22.5% | 50.3% | 27.3% | −0.048 |

**Conclusion (diagnostic): directionally present but weak and threshold-like.**
`P(DOWN)` is flat at ~35% through Q1–Q3 then drops to 27% in Q5; `P(UP)` edges up
from 18% to 23%. The mean UP−DOWN share is −0.082 across Q4–Q5 versus −0.161
across Q1–Q3 — the "tighter system → upward pressure" mechanism appears only once
the system is actually tight, not as a smooth gradient (gradient Spearman +0.70).
Association Spearman(actual residual load, signed spread) = +0.057, 95% CI
[+0.043, +0.070] — right sign, real, small.

**Relation to H2.** H2 fails exactly where the system is wind-poor / tight
(P4.4), which is the high-residual-load Q4–Q5 region where H1's directional
effect concentrates. H1 and H2 look **complementary rather than redundant**; a
joint transparent rule is P7.

### P5.2 — H1-B Decision-Eligible Proxy Assessment

**Run:** 2026-09-06. Evidence:
`research/evidence/p5_h1_residual_load/p5_2_h1b_assessment_2026-09-06.json`.

Proxy: `residual_load_known_mwh = consumption_climatology_mwh −
renewable_forecast_5h_mwh`, where the climatology is a point-in-time expanding
mean of gross consumption over prior same-(weekday, hour) occurrences lagged 3
occurrences past the settlement delay, and the renewable forecast is the 5h
offshore + onshore + solar forecast. Both inputs are available strictly before
delivery (D025). Available for 21,184 / 21,887 hours.

- The proxy tracks actual residual load well: Spearman +0.92 (n = 21,184).
- It reproduces the H1 direction (gradient Spearman +0.90; association with the
  spread +0.042, right sign, CI excludes zero) — but that association is as weak
  as H1-A.

**Verdict / registration:** `ELIGIBLE_INTERIM_PROXY`. A decision-eligible
residual-load proxy is feasible and carries the H1 direction; register it as an
eligible input for the P7 signal engine, **not** a standalone signal. A stronger
H1-B still needs the external ENTSO-E day-ahead total-load forecast (I06,
pending access).

## H2 — Renewable Forecast Revision

**Status:** P4.1–P4.4 complete 2026-09-06 — round 1 **SUPPORTED (weak,
asymmetric)**; after conditioning (P4.4) **CONDITIONALLY SUPPORTED** — real
mechanism (permutation p < 0.05), robust to season and hour-of-day, but it fails
at low expected wind and does not reproduce on a 2024 H1 chronological hold-back.
Cross-border conditioning is H3 / P6.
**Role:** Primary MVP hypothesis

### Question

Do renewable forecast revisions contain information about the direction of balancing pressure?

### Candidate Variable

`Forecast Revision = Forecast1Hour - Forecast5Hour`

A positive wind revision means expected wind production increased as delivery approached. All directional relationships must be tested rather than assumed.

### Point-in-Time Constraint

P1.1 established same-hour fixed-horizon fields with approximately 99% numeric
pair coverage in the development period. P2.3 fixed the decision anchor at the
delivery-hour start and permits only information available strictly before it.
Non-null 5h and 1h fields qualify at this last-pre-delivery snapshot under the
official source rule; no earlier exact-minute or complete tick-by-tick vintage
claim is allowed. Use the documented missingness, zero-value and DST rules.
P1.2 fixed the same-hour DK1 day-ahead reference as
`Elspotprices.SpotPriceEUR` in EUR/MWh with complete development-period
coverage. P1.3 fixed the ex-post balancing outcome as
`RegulatingBalancePowerdata.ImbalancePriceEUR` in EUR/MWh. Its official
development extract is missing one complete DST fall-back hour, which must
remain missing rather than be filled with zero.

### P4.1 Pre-Registered Test Specification

**Registered:** 2026-09-06, before any revision variable was constructed and
before any revision-outcome relationship was inspected. Frozen machine-readable
snapshot: `research/evidence/p4_h2_revision/p4_1_preregistration_2026-09-06.json`.
Everything below is fixed in advance; P4.2 fills in only the development-derived
numbers (bucket edges, group sizes, coverage, normalization floor) without
changing the procedure.

**Tested relationship.** Whether the 5h-to-1h renewable forecast revision for a
DK1 delivery hour carries information about that same hour's realized
balancing-pressure outcome — the frozen label (`UP` / `DOWN` / `NEUTRAL`,
`delta = 5.9956075 EUR/MWh`, D026) and the frozen continuous signed spread.

**Revision variable.** For each DK1 delivery hour `t` and forecast type
`k in {Offshore Wind, Onshore Wind, Solar}`:

`revision_k,t = Forecast1Hour_k,t - Forecast5Hour_k,t` (MWh)

computed only when both horizon fields are non-null in the same
`HourUTC + PriceArea + ForecastType` row (D021). Wind is aggregated as
`wind_revision_t = revision_OffshoreWind,t + revision_OnshoreWind,t`, computed
only when all four wind horizon fields are non-null. Raw MWh is the primary
scale. A secondary normalized form `wind_revision_t / wind_forecast_5h_t` is
reported only where `wind_forecast_5h_t` is at or above a development-distribution
floor fixed in P4.2, to avoid divide-by-near-zero.

**Primary and secondary tests.**

- **Primary — wind.** `wind_revision_t` in raw MWh. This test alone determines
  whether "H2 is supported". DK1 has a very high wind share and wind is the
  dominant renewable driver of physical imbalance.
- **Secondary — solar.** `solar_revision_t` runs the *same* full procedure
  (buckets, association, rule, chart, baselines) with its own success/failure
  judgment, on both the all-numeric-pairs set and the both-horizons-positive
  daytime subset (D021). A solar-only positive result is reported as
  **conditionally supported — solar only, needs replication**, never as "H2
  supported".
- Offshore-only, onshore-only and combined wind+solar revisions are exploratory
  in round 1.

**Expected direction (pre-registered and falsifiable).** Mechanism: a positive
wind revision means more wind is expected as delivery approaches, implying a
looser expected balance and a higher probability that the hour settles as `DOWN`
pressure (balancing price below the already-cleared day-ahead). A negative
revision implies the reverse and favours `UP`. On development data we predict:

- `P(DOWN | wind_revision in the top bucket) > P(DOWN | wind_revision in the middle bucket)`;
- `P(UP | wind_revision in the bottom bucket) > P(UP | wind_revision in the middle bucket)`;
- a directionally consistent gradient in the `DOWN`-share minus `UP`-share across
  ordered revision buckets;
- a negative rank association between signed `wind_revision_t` and the signed
  spread.

Contrary-direction and no-relationship outcomes are both admissible results and
must be reported, not discarded (D008, D013).

**Buckets.** `wind_revision_t` is cut into five ordered groups by its
development-only signed quantiles Q20 / Q40 / Q60 / Q80, computed in P4.2 and
frozen before any outcome comparison. A ten-group signed-decile view is reported
as a secondary check in case the relationship is concentrated in the tails. No
hand-picked "strong revision" magnitude threshold is used in round 1; the
quantile grid lets a monotone pattern appear or fail to appear on its own.
Bucket edges, group sizes and tie handling are recorded in P4.2 evidence.

**Test method (round 1 — descriptive and conditional, per the D013 modelling
order).**

1. Contingency table: revision bucket by frozen label, with row and column
   shares and group sizes (five-quantile primary, ten-decile secondary).
2. Rank association between signed `wind_revision_t` and the outcome:
   - primary: Spearman correlation with the frozen continuous signed spread
     (EUR/MWh), with a bootstrap confidence interval on development data;
   - secondary: Spearman with the ordinal label score (`+1` `UP`, `0` `NEUTRAL`,
     `-1` `DOWN`).
3. A transparent rule — predict `DOWN` if `wind_revision_t > c`, `UP` if
   `wind_revision_t < -c`, else `NEUTRAL` — with `c` fixed at the frozen
   development Q60 revision magnitude (pre-registered, not tuned). Score it on
   three-class balanced accuracy and macro-F1.
4. One chart: `DOWN` / `UP` / `NEUTRAL` share by revision bucket (also satisfies
   the Level A "meaningful chart" criterion).

**Baselines.** All three are computed and reported (D012):

- majority class, fit on training labels only;
- hour-of-week training majority (availability-safe supplement, D026);
- persistence `y_hat_t = y_(t-1)`, retained as an ex-post reference.

The rule's pass/fail is judged only against the two availability-safe baselines
(majority and hour-of-week). Persistence is `ex_post_reference_only` and
`decision_feature_eligible: false` (D023, E001) — it cannot be proven available
at the decision cutoff, so it is not a pass/fail gate. It is still reported
prominently: if the rule does not beat persistence, the write-up states that and
defers "does the revision add information beyond lagged state" to the P10
multivariate stage.

**Success and failure criterion (pre-registered).** The primary wind test is
**supported** only if all three hold on the development sample:

- the `DOWN`-minus-`UP` share gradient is monotone in the predicted direction
  across at least four of the five quantile buckets;
- the primary Spearman interval excludes zero with the predicted (negative)
  sign;
- the transparent rule beats both availability-safe baselines (majority and
  hour-of-week) on both balanced accuracy and macro-F1, reported with the
  in-sample delta caveat (E002).

If the gradient and association hold but the rule does not beat those baselines,
the conclusion is **conditionally supported / mechanism only** — mechanism
evidence is reported and no edge is claimed. If neither holds, the conclusion is
**rejected / null**, which is a valid completed test (D013, D017) and is
retained in full. The solar secondary test uses the identical bar for its own
separate judgment.

**Counterargument.** The day-ahead and intraday markets may already absorb the
forecast update, so by delivery the balancing outcome could be driven more by
outages, cross-border flows and demand surprises than by the renewable revision.
A raw association may also reflect season or regime confounding rather than
information content.

**Invalidation.** If conditioning on season, hour-of-day regime or cross-border
capacity (H3 / P6) removes the gradient, H2 is at best conditional. If P4.2
diagnostics show the 5h and 1h values are not independent pre-delivery
observations (for example a large share of hours where `Forecast5Hour` equals
`Forecast1Hour` exactly), the revision variable's information content is
reinterpreted or the test is paused.

**P4.2 diagnostics to report before any outcome comparison.**

- Share of eligible hours where `Forecast5Hour == Forecast1Hour` exactly
  (forecast never updated) and the mass within a small `±epsilon` band;
- coverage: hours with a non-null `wind_revision_t`, hours dropped for missing
  horizons, per forecast type;
- the frozen five-quantile and ten-decile bucket edges and group sizes;
- the normalization floor for `wind_forecast_5h_t`.

**Denominators to disclose (E002, D021).** Total development hours; hours with a
valid frozen label (21,886); hours with a non-null `wind_revision_t`; hours
dropped for missing horizons; the single missing-target hour
(`2022-10-30T00:00:00Z`); solar all-pairs versus both-positive counts.

**Deferred to P4.4 (not round 1).** Regime conditioning
(tight / normal / loose, renewable level), cross-border conditioning, any
magnitude-threshold rule tuning, logistic regression and probability
calibration.

### P4.3 Round-1 Result

**Run:** 2026-09-06, exactly as pre-registered (P4.1 / D027); nothing chosen at
run time. Evidence: `research/evidence/p4_h2_revision/p4_3_*`
(`p4_3_wind_primary_2026-09-06.json`, `p4_3_solar_secondary_2026-09-06.json`,
`p4_3_result_2026-09-06.md`, `p4_3_revision_label_chart_2026-09-06.png`,
`p4_3_quality_report_2026-09-06.json` with 9/9 checks). Development only,
in-sample / descriptive (E002).

**Primary — `wind_revision` (raw MWh). Conclusion: SUPPORTED — weak, asymmetric
effect.**

Sample: 21,614 development hours with a non-null wind revision and a valid label.

`P(label | signed wind_revision quintile)`:

| Bucket | P(UP) | P(NEUTRAL) | P(DOWN) | DOWN-share − UP-share |
|---|---:|---:|---:|---:|
| Q1 (most negative) | 24.7% | 48.1% | 27.3% | +0.026 |
| Q2 | 20.8% | 50.2% | 29.0% | +0.082 |
| Q3 | 19.0% | 47.4% | 33.6% | +0.146 |
| Q4 | 17.9% | 46.3% | 35.8% | +0.180 |
| Q5 (most positive) | 17.2% | 44.1% | 38.7% | +0.215 |

The `DOWN`-minus-`UP` share rises monotonically across all five buckets (gradient
Spearman +1.00, endpoints Q5 > Q1). As the 5h-to-1h wind forecast is revised
upward, the delivery hour becomes more likely to settle `DOWN` and less likely
`UP` — the pre-registered mechanism direction. Between the extreme buckets the
`DOWN` share moves ~11 points (27.3% → 38.7%) and the `UP` share ~7.5 points
(24.7% → 17.2%).

Association: Spearman(signed `wind_revision`, signed spread) = **−0.096**, 95%
bootstrap CI [−0.109, −0.083] (2,000 draws, seed 20260906). The sign is negative
as predicted and the CI excludes zero, but `|rho| ~ 0.1` is a weak association.
Secondary Spearman vs the `+1/0/-1` label score = −0.099.

Transparent rule (`DOWN` if `wind_revision > 128.083 MWh`, `UP` if
`< -128.083`, else `NEUTRAL`):

| Method | Balanced accuracy | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| Revision rule | 0.365 | 0.362 | 0.422 |
| Majority (`NEUTRAL`) | 0.333 | 0.214 | 0.472 |
| Hour-of-week training majority | 0.345 | 0.264 | 0.475 |
| Persistence (ex-post reference) | 0.699 | 0.699 | 0.714 |

The rule beats both availability-safe baselines on balanced accuracy and macro-F1,
so the pre-registered "supported" bar is met. The margin is small; the rule
*loses* to those baselines on plain accuracy, and it is far below the ex-post
persistence reference. Its directional skill is asymmetric: on the `DOWN` side it
is real (2,032 correct vs 901 opposite-direction calls), on the `UP` side it is
essentially absent (845 correct vs 907 opposite-direction). Much of the
balanced-accuracy edge comes simply from attempting `UP`/`DOWN` calls, which the
`NEUTRAL`-only baselines never do.

**Secondary — `solar_revision`. Conclusion: conditionally supported — solar only,
needs replication** (both the all-numeric-pairs and the both-horizons-positive
daytime subsets). Same monotone gradient and same predicted-sign association, but
weaker (Spearman −0.060 all pairs, −0.075 daytime). `c` for solar was derived by
the frozen formula (Q60 of `abs(solar_revision)`) at run time because P4.2 only
persisted the wind threshold. Not counted toward "H2 supported".

**Counterargument and limitations.**

- In-sample and descriptive; the frozen delta was estimated on the same period
  (E002). A chronological out-of-sample check is P4.4 / P10.
- The round-1 rule-vs-baseline gate rewards a method merely for attempting all
  three classes. A stricter future test should require beating a directional
  baseline or use a proper scoring rule. Carried to P4.4.
- The effect may be confounded by season or hour-of-day regime, or offset by
  cross-border capacity — P4.4 and H3 test this.
- Balancing pressure is an ex-post proxy, not executable trading P&L (D016).

**Invalidation status.** The 5h and 1h values are genuine distinct pre-delivery
snapshots (P4.2: the wind forecast moved in every wind-aggregate hour), so the
revision variable is valid. If P4.4 regime or cross-border conditioning removes
the gradient, H2 is downgraded to conditional.

### P4.4 Conditioning and Failure Analysis

**Run:** 2026-09-06. Exploratory / descriptive (E002); the regime bins, the
chronological split date and the permutation seed were declared before any
outcome was crossed. Evidence:
`research/evidence/p4_h2_revision/p4_4_conditioning_2026-09-06.{json,md}`,
`p4_4_regime_gradient_chart_2026-09-06.png`, `p4_4_quality_report_2026-09-06.json`
(7/7).

**Conclusion: CONDITIONALLY SUPPORTED.** The mechanism is real but not robust
enough for decision use as it stands.

1. **The rule uses real information.** Permutation null (shuffle `wind_revision`
   500 times, seed 20260906): observed balanced accuracy 0.3647 vs null max
   0.3426, p ≈ 0.000. The weak edge is not chance.
2. **Robust to season and hour-of-day.** The gradient is directionally consistent
   (gradient Spearman ≥ 0.9, Q5−Q1 `P(DOWN)−P(UP)` spread positive) in all four
   seasons and all four hour-of-day blocks. Strongest in summer (+0.359) and
   midday (+0.249); weakest in winter (+0.115).
3. **Documented failure — low expected wind.** Split by 5h wind-forecast
   terciles, the gradient holds for mid wind (Spearman +1.00, spread +0.288) and
   high wind (+0.90, +0.119) but collapses to noise at low wind (+0.30, +0.047).
   When the system is already wind-poor, a marginal wind revision no longer
   moves the balancing outcome.
4. **Does not reproduce out-of-time.** Train `< 2024-01-01` (17,408 h), validate
   2024-01-01..2024-06-30 (4,207 h; partial year). Refreezing the quintile edges,
   `c` and the hour-of-week baseline on train, the validate gradient Spearman is
   +0.10 and Spearman(revision, spread) is −0.015 — the effect is essentially
   absent. The window is small and seasonally confounded, so this is a warning,
   not proof; the Level C holdout is the real test.

**Implication for decision use.** H2 is conditional on expected wind not being
low, and its stability out-of-time is unproven. It is a population-level
mechanism finding, not a deployable hour-by-hour edge. Cross-border conditioning
(H3 / P6), a logistic model and calibration (P10), and the locked-holdout
evaluation (Level C) remain.

## H3 — Cross-Border and System Conditions

**Status:** Sources registered; testing not started
**Role:** Conditional hypothesis

### Question

Do cross-border conditions change the relationship between renewable forecast revisions and balancing pressure?

### Mechanism

Available transmission capacity, scheduled exchange and neighboring-market conditions may absorb or amplify local DK1 imbalances.

### Point-in-Time Constraint

Each cross-border field must be classified as decision eligible, diagnostic only or unavailable before use.

P1.4 registered `Transmissionlines.ImportCapacity`, `ExportCapacity` and
`ScheduledExchangeDayAhead` as conditional decision candidates. P2.3 confirmed
their timing at the last-pre-delivery cutoff; P6.1 must still handle
border-specific coverage, nulls and mixed export-capacity signs. Final
intraday schedules and physical settlement flows are diagnostic only.

Legacy `CountertradeIntraday` is a partial-period conditional candidate from
2023-04-18. P2.3 found 7,469 stored rows published strictly before delivery and
282 stored rows unavailable at the cutoff. Later versions overwrite earlier
history, and absent publication days do not mean zero. The 2025 successor is
unavailable for development.

## Research Rule

Each hypothesis must retain:

- Original question
- Market mechanism
- Eligible inputs
- Test specification
- Result
- Counterargument
- Invalidation condition
- Final conclusion

A null or failed result remains part of the research record.
