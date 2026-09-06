# P8.1 — Level A Acceptance Audit

**Date:** 2026-09-06
**Auditor pass:** each criterion checked against committed evidence at
`git HEAD = 2de4fe1` (the P4.3 commit).
**Result: 10 / 10 criteria met — Level A (CV-safe) evidence gate PASSED.**
**Holdout:** LOCKED, fetch-disabled, zero rows read.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| A1 | Repository created | DONE | Local git repo; private GitHub remote `yifanwang-mvrk/dk1-power-market-research`; `main` synced; 10 phase commits P0 -> P4.3 |
| A2 | Professional README | DONE | `README.md` — question, target formula, periods, validated source roles, pipeline, target construction, principles; states the no-executable-P&L boundary. P8.2 adds the H2 result and the Level A line |
| A3 | Project Charter | DONE | `research/project_charter.md` — mission, question, primary outcome + formula, hypotheses, periods, PIT policy, mandatory baselines, scope boundaries, completion principle. P8.2 refreshes the status line |
| A4 | Target and periods frozen in config | DONE | `config/research_config.yaml` — development 2022-01-01..2024-06-30; holdout 2024-07-01..2024-12-31 `state: locked`, `fetch_allowed: false`; target `ImbalancePriceEUR - SpotPriceEUR` EUR/MWh; `numerical_delta: 5.9956075` `status: frozen`. D001/D002/D004/D005/D022/D023/D026 |
| A5 | Core forecast, day-ahead and balancing data fetched | DONE | `data/raw/p1_1_validation/`, `p1_2_validation/`, `p1_3_validation/` hold full-development raw JSON; P1.1/P1.2/P1.3 validation evidence; P2 joined all sources into 21,887 development hours. D020–D023 |
| A6 | Data dictionary with all three PIT classes | DONE | `data/data_dictionary.md` — every registered field carries `decision_eligible` / `diagnostic_only` / `outcome` (plus documented conditional variants); explicit "Point-in-Time Classes" section. D006/D024 |
| A7 | H2 revision variables constructed | DONE | P4.2 — `src/p4_revision.py`, `data/processed/p4/revision_development.parquet`; wind and solar 5h-to-1h revisions; 21,615 wind-aggregate hours; buckets and rule threshold frozen; `p4_2_*` evidence, 12/12 checks. D027 |
| A8 | At least one completed hypothesis test with a written conclusion | DONE | P4.3 — H2 round-1, pre-registered (D027), conclusion **SUPPORTED (weak, asymmetric)** with full magnitude, asymmetry and limitations in `research/hypotheses.md` and `p4_3_result_2026-09-06.md`; `p4_3_*` evidence, 9/9 checks. D028. A null result would also have qualified |
| A9 | At least one meaningful chart | DONE | `research/evidence/p4_h2_revision/p4_3_revision_label_chart_2026-09-06.png` — balancing-pressure label share by signed wind-revision quintile; shows the monotone DOWN/UP gradient |
| A10 | Holdout completely unused | DONE / MAINTAINED | All API request boundaries end exclusive at local 2024-07-01; near-boundary probes use `limit=0` (metadata only); every processed table maxes at 2024-06-30 21:00 UTC; the P3 and P4 loaders abort unless `holdout.state == locked` and `fetch_allowed is False`; zero holdout rows in `hourly_base_development`, `target_development` or `revision_development` |

## Notes carried forward

- **P8.2:** update `README.md` and `research/project_charter.md` so their wording
  matches completed work — add the H2 round-1 result and its limitations, and the
  Level A status — without overstating (no profitable-strategy or executable-P&L
  language, D016/D018).
- **P4.4 (Level B):** the round-1 rule-vs-baseline gate was lenient (balanced
  accuracy rewards attempting all three classes); a stricter gate and a
  chronological out-of-sample check are required. Plus season / regime and
  cross-border conditioning of the H2 gradient.

## Verdict

Level A — CV-safe: **ACHIEVED** on the evidence gate. P8.2 factual-wording polish
is the remaining packaging task; it does not change the achievement.
Level B and Level C: not started.
