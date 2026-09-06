# P9.2 — Level B Acceptance Audit

**Date:** 2026-09-06
**Auditor pass:** each criterion checked against committed evidence at
`git HEAD = fe53475` (the P7 commit) plus the P9.1 memo.
**Result: 10 / 10 criteria met — Level B (Interview Ready) ACHIEVED.**
**Holdout:** LOCKED, fetch-disabled, zero rows read.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| B1 | H2 complete first round | DONE | P4.1 pre-registration (D027), P4.3 round-1 test (D028: supported, weak, asymmetric), P4.4 conditioning (D030: conditionally supported — real by permutation, fails at low wind, no out-of-time reproduction). `research/evidence/p4_h2_revision/`, `research/hypotheses.md` |
| B2 | H1 mechanism research + H1-B eligibility | DONE | P5.1 H1-A (D031: diagnostic, weak threshold-like, concentrated where H2 fails); P5.2 H1-B climatology proxy registered `ELIGIBLE_INTERIM_PROXY` (tracks actual residual load Spearman +0.92). `research/evidence/p5_h1_residual_load/`, `config/research_config.yaml` |
| B3 | H3 preliminary conditioning, eligible vs diagnostic | DONE | P6 (D032): decision-eligible day-ahead capacity / schedule do not condition the H2 gradient; realized net-import flow shows a weak *diagnostic* steepening; no decision-eligible H3 signal. `research/evidence/p6_h3_cross_border/` |
| B4 | Transparent rule-based signal (UP / DOWN / NO TRADE) | DONE | P7.1 (D033): a stated decision table over decision-eligible inputs only; H2 → DOWN only, H1-B → UP only, NO TRADE otherwise; thresholds pre-declared. `src/p7_signal_engine.py`, `config/research_config.yaml` `signal_engine` |
| B5 | Confidence levels with a stated basis | DONE | P7.2: Low / Medium / High scale; DOWN view (H2) MEDIUM, UP view (H1 proxy) LOW, **no case supports High**, with the P4.3 / P5.1 basis stated. `research/evidence/p7_signal_engine/p7_signal_engine_2026-09-06.md` |
| B6 | Risk / invalidation per view | DONE | P7.2 and each Market State Card: key risk (unseen shocks), invalidation (low 5h wind forecast, renewables far from forecast, system turning tight), No Trade conditions |
| B7 | Market State Card (>= 1 real development example) | DONE | 4 cards (`market_state_card_1..4_2026-09-06.md`) — real development hours, decision fields plus retrospective outcome and post-mortem, labelled not-live |
| B8 | First Market Journal entry | DONE | `journal/market_journal.md` J001 — the H1/H2/H3 first-round post-mortem: what held, what was missing, what changes |
| B9 | Short research memo | DONE | `research/r01_research_memo.md` v1.0 — question, method, H1/H2/H3 results and limitations, the signal and its baseline comparison, risk/invalidation, and what Level C decides |
| B10 | Majority + persistence baseline comparison in scorecard form | DONE | P7.3 scorecard: signal vs majority, hour-of-week and persistence (ex-post reference) on balanced accuracy, macro-F1 and accuracy, with coverage and No Trade denominators; collated in the memo |

## Interview talking points (P9.2 "explain the findings")

1. **The discipline is the deliverable.** Frozen target and δ, pre-registered
   primary test, a holdout that has never been touched, naive baselines on every
   result. This is what separates a signal from a base rate.
2. **H2 is real but weak.** Positive wind revisions shift the hour toward DOWN
   (P(DOWN) 27% → 39% across revision quintiles), the permutation null rejects
   chance, but |Spearman| ≈ 0.1 and it did not reproduce on 2024 H1.
3. **Know where it breaks.** H2 fails when wind is low; H1 (tight system) picks
   up exactly there. The two are complementary.
4. **Be honest about what is not usable.** H3 day-ahead cross-border capacity
   adds nothing; only realized flow (diagnostic) interacts with H2.
5. **No Trade is a decision.** The transparent engine abstains ~two thirds of
   the time and only claims a modest DOWN-side edge.
6. **Level C is the real test.** A logistic model, calibration, one holdout
   evaluation — and a null result still completes the MVP.

## Verdict

Level B — Interview Ready: **ACHIEVED**. Level C (P10: logistic regression,
calibration, the locked-holdout unlock and evaluation) is the next and final
MVP milestone.
