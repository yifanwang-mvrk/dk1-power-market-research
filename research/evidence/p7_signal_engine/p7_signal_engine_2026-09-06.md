# P7 — Transparent Signal Engine

**Status:** P7.1–P7.3 complete — 2026-09-06
**Scope:** development only, in-sample / descriptive (E002); research judgment,
not executable trading P&L (D016)
**Holdout:** LOCKED AND UNUSED

## P7.1 — the decision table (decision-eligible inputs only)

Pre-declared thresholds:
`h2_strong_cut = 222.6 MWh`
(top 20% of `abs(wind_revision)`),
`low_wind_cut = 861.4 MWh` (P4.4 blind spot),
`rl_tight_cut = 1855.7 MWh` (top 20% of the H1-B proxy).

- **H2 view:** DOWN if `wind_revision > h2_strong_cut` and
  `wind_forecast_5h > low_wind_cut`; else none. H2 does **not** emit UP — P4.3
  showed the UP side has no skill.
- **H1 view:** UP if `residual_load_known > rl_tight_cut`; else none. H1 does
  **not** emit DOWN — P5.1 supported only the tight, UP side.
- **Combination:**
  - `DOWN PRESSURE` / MEDIUM — H2 DOWN, H1 not tight
  - `UP PRESSURE` / LOW — H1 very tight, H2 not on the DOWN side
  - `NO TRADE` — H2 DOWN vs H1 tight conflict; neither view fires; or a missing input

## P7.2 — confidence, No Trade, risk

- Confidence scale Low / Medium / High. **Nothing in this round supports High.**
  The DOWN view (H2, the evidenced side) is MEDIUM; the UP view (H1 proxy, weaker)
  is LOW.
- No Trade conditions: conflicting views, neither view fires, any missing
  decision-eligible input.
- Every active view carries the same risk (hourly outcomes dominated by unseen
  shocks) and invalidation (low 5h wind forecast; renewables far from forecast;
  the system turning tight against a DOWN view).

## P7.3 — scoring against the mandatory baselines

Denominators: 21,887 development hours,
21,886 with a valid label, 7,154
active views (32.7% coverage),
14,732 No Trade.

Full sample (No Trade scored as a NEUTRAL prediction):

| Method | Balanced accuracy | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| P7 signal | 0.3473 | 0.3320 | 0.4126 |
| Majority (NEUTRAL) | 0.3333 | 0.2139 | 0.4725 |
| Hour-of-week training majority | 0.3442 | 0.2612 | 0.4750 |
| Persistence (ex-post reference) | 0.6994 | 0.6994 | 0.7145 |

Active-view three-class hit rate: 0.2892
over 7,154 hours
(MEDIUM 0.40020435967302453, LOW 0.2119487908961593).

Realized label within each signal class:

| Signal | Hours | P(UP) | P(NEUTRAL) | P(DOWN) |
|---|---:|---:|---:|---:|
| UP PRESSURE | 4,218 | 21.2% | 50.3% | 28.5% |
| DOWN PRESSURE | 2,936 | 17.1% | 42.9% | 40.0% |
| NO TRADE | 14,732 | 20.1% | 47.3% | 32.7% |

## Artefacts

- Market State Cards: ['market_state_card_1_2026-09-06.md', 'market_state_card_2_2026-09-06.md', 'market_state_card_3_2026-09-06.md', 'market_state_card_4_2026-09-06.md']
- Market Journal entry: journal/market_journal.md J001
- Chart: `p7_signal_vs_label_chart_2026-09-06.png`

## Limitations

- In-sample / descriptive; thresholds are pre-declared from decision-eligible
  distributions but the whole development delta and buckets were estimated on the
  same period (E002).
- No probabilistic output yet (P10). Not executable trading P&L (D016).
