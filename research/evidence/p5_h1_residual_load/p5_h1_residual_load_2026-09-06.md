# P5 — H1 Residual Load and System Tightness

**Status:** P5.1 and P5.2 complete — 2026-09-06
**Holdout:** LOCKED AND UNUSED

## H1-A (P5.1) — actual residual load, diagnostic

`residual_load_actual_mwh = actual_gross_consumption - sum(actual wind) - sum(actual solar)`.
Settlement data, published ~9-15 days after delivery and later revised (D024):
this explains realized physical conditions and is **never a decision input**.
Available for 21,887 / 21,887 hours;
5,974 hours have negative residual
load (wind + solar exceeded consumption) and are preserved.

`P(label | signed actual-residual-load quintile)`:

| Bucket | Hours | P(UP) | P(NEUTRAL) | P(DOWN) | UP-share − DOWN-share |
|---|---:|---:|---:|---:|---:|
| Q1 | 4,378 | 18.4% | 47.1% | 34.6% | -0.162 |
| Q2 | 4,377 | 19.1% | 46.0% | 34.9% | -0.158 |
| Q3 | 4,376 | 19.6% | 44.5% | 35.9% | -0.163 |
| Q4 | 4,377 | 19.9% | 48.4% | 31.6% | -0.117 |
| Q5 | 4,378 | 22.5% | 50.3% | 27.3% | -0.048 |

Gradient (bucket index vs UP−DOWN share) Spearman:
`+0.70` — directionally consistent:
**False**. The UP-vs-DOWN shift is concentrated
in the tightest hours: mean UP−DOWN share is
`-0.082` across
Q4-Q5 vs
`-0.161`
across Q1-Q3.

Association Spearman(actual residual load, signed spread):
`+0.0568`, 95% CI [`+0.0430`,
`+0.0702`], predicted sign positive, supported:
**True**

**Conclusion (diagnostic): directionally present but weak and threshold-like (diagnostic) — the shift toward UP and away from DOWN appears only in the tightest ~40% of hours (Q4-Q5), not as a smooth gradient**

**Relation to H2:** H2 (P4.4) fails exactly where the system is wind-poor / tight, which is the high-residual-load Q4-Q5 region where H1's directional effect concentrates. H1 and H2 look complementary rather than redundant; a joint transparent rule is P7.

## H1-B (P5.2) — is there a decision-eligible proxy?

`residual_load_known_mwh = consumption_climatology_mwh - renewable_forecast_5h_mwh`,
where the climatology is a point-in-time expanding mean of gross consumption over
prior same-(weekday, hour) occurrences lagged 3
occurrences past the settlement delay, and the renewable forecast is the 5h
offshore + onshore + solar forecast. Both inputs are available strictly before
delivery (D025). Available for 21,184 /
21,887 hours.

- Proxy vs actual residual load: Spearman `+0.924` (n =
  21,184) — how well the eligible proxy tracks the realized quantity.
- `P(label | signed known-residual-load quintile)`:

| Bucket | Hours | P(UP) | P(NEUTRAL) | P(DOWN) | UP-share − DOWN-share |
|---|---:|---:|---:|---:|---:|
| Q1 | 4,237 | 19.0% | 46.3% | 34.7% | -0.157 |
| Q2 | 4,237 | 18.8% | 45.5% | 35.7% | -0.169 |
| Q3 | 4,235 | 21.4% | 43.3% | 35.3% | -0.140 |
| Q4 | 4,237 | 19.4% | 49.7% | 30.9% | -0.115 |
| Q5 | 4,237 | 21.2% | 50.2% | 28.6% | -0.074 |

- Gradient Spearman `+0.90`, directionally
  consistent: **True**
- Association Spearman(known residual load, signed spread):
  `+0.0419`, 95% CI [`+0.0288`,
  `+0.0552`], supported: **True**

**Verdict: A decision-eligible residual-load proxy is feasible: it tracks actual residual load well (Spearman +0.92) and reproduces the H1 direction, though its own association with the spread is as weak as H1-A (Spearman +0.042). Register it as an eligible input for P7, not a standalone signal.**
**Registration status: ELIGIBLE_INTERIM_PROXY**

P1.4 found no validated Energi Data Service historical load forecast; the ENTSO-E
day-ahead total-load forecast remains an external candidate pending access (I06).

## Limitations

- H1-A is diagnostic only and in-sample / descriptive (E002).
- The H1-B climatology proxy uses a simple expanding hour-of-week mean; it does
  not model holidays, temperature or load growth beyond the trailing average.
- The true out-of-sample test is the Level C holdout.
