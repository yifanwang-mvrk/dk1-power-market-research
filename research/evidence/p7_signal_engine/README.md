# P7 — Transparent Signal Engine Evidence

**Status:** P7.1–P7.3 complete 2026-09-06 — Level B B4–B8 done
**Holdout:** LOCKED AND UNUSED

`src/p7_signal_engine.py` builds a small decision table over decision-eligible
inputs only and scores it against the mandatory baselines. Tests:
`tests/test_p7_signal_engine.py`. Quality gate:
`p7_quality_report_2026-09-06.json` (9/9). In-sample / descriptive (E002);
research judgment, not executable trading P&L (D016). Decision D033.

## The rule (P7.1 / P7.2)

Pre-declared thresholds from decision-eligible distributions:
`h2_strong_cut` = 222.6 MWh (top 20% of `abs(wind_revision)`),
`low_wind_cut` = 861.4 MWh (P4.4 blind spot),
`rl_tight_cut` = 1855.7 MWh (top 20% of the H1-B proxy).

- **H2 view** → `DOWN` only, when `wind_revision > h2_strong_cut` and
  `wind_forecast_5h > low_wind_cut`. H2 never emits `UP` (P4.3 asymmetry).
- **H1 view** → `UP` only, when `residual_load_known > rl_tight_cut`. H1 never
  emits `DOWN` (P5.1 supported only the tight side).
- **Combination:** `DOWN PRESSURE` (MEDIUM) when H2 fires and H1 is not tight;
  `UP PRESSURE` (LOW) when H1 is tight and H2 is silent; `NO TRADE` on conflict,
  silence or a missing input. **No case supports High confidence.**

## Result (P7.3)

- Active view in 32.7% of hours (7,154 active, 14,732 No Trade).
- `DOWN PRESSURE` hours realize `DOWN` **40.0%** vs a 32.9% base rate (+7 pp).
- `UP PRESSURE` hours realize `UP` 21.2% vs 19.9% (+1.3 pp, negligible).
- Balanced accuracy 0.347 vs majority 0.333 and hour-of-week 0.344 (marginal
  win); plain accuracy 0.413 vs ~0.47 (loss); far below persistence (ex-post).
- MEDIUM-confidence active views hit 0.40 (three-class) vs 0.21 for LOW — the
  confidence tiering is meaningful.

**Conclusion:** a modest, DOWN-side, in-sample edge that correctly abstains two
thirds of the time. Not a deployable signal.

## Artefacts

- `market_state_card_1..4_2026-09-06.md` — retrospective worked examples (hits, a
  miss, a No Trade).
- `journal/market_journal.md` J001 — first research-round post-mortem.
- `p7_signal_vs_label_chart_2026-09-06.png`.

## Next steps

| Step | Action |
|---|---|
| P9 | `research/r01_research_memo.md` — collate H1/H2/H3, the signal and its baselines, limitations |
| P10 | Logistic model + calibration in development; then the Level C locked-holdout test |
