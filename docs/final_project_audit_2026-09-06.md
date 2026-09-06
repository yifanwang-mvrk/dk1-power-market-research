# Final Project Audit — 2026-09-06

**Scope:** completed DK1 MVP, P1 through P10.4, at post-completion `main`.
**Verdict:** PASS, with documentation-state corrections recorded below.
**Holdout:** evaluated once under D037 and closed. This audit did not rerun,
refetch, retune or reclassify the holdout.

## Verification performed

| Area | Check | Result |
|---|---|---|
| Git | Branch and remote alignment; object integrity; whitespace | `main` aligned with `origin/main` before the audit; no corrupt objects; no diff errors |
| Environment | `uv.lock` consistency and Python compilation | PASS |
| Tests | `python -m unittest discover -s tests -v` | 50 / 50 PASS |
| Evidence | Parse every committed evidence JSON | 80 / 80 parsed |
| Hash chain | P1 raw to P2, P2 to P3, P3 to P4, and P10 raw provenance | 15 / 15 matched |
| Development scope | Unique real-hour UTC spine; no row at or after the holdout start | 21,887 / PASS |
| Holdout scope | Local 2024 H2 window; unique UTC hours | 4,417 / PASS |
| P3 target | Recompute spread and frozen-delta labels | Exact match: 4,354 UP, 7,190 DOWN, 10,342 NEUTRAL, 1 missing |
| P7 | Rebuild transparent rule and recompute stored metrics | Exact match |
| P10 | Refit the frozen development model locally and recompute holdout raw/calibrated metrics without writing results | Exact match on 4,331 scored hours |
| Visual evidence | Inspect all seven charts | PASS; readable and directionally consistent with the stored metrics |
| PDF references | Extract text and render every page of the 29-page handbook and 7-page overview | PASS; no blank, clipped or broken page |
| Repository hygiene | Raw/processed datasets ignored; no tracked caches or obvious credentials | PASS |

## Corrections made by this audit

1. The generated P10.3 result page called the final result D036. D036 is the
   unlock record; D037 is the owner-approved one-shot result. The generator and
   generated Markdown now say D037.
2. The final memo still said that the holdout had never been accessed and listed
   40 tests. It now records the one approved evaluation and the current 50-test
   suite.
3. The model config and one status-board line still said the holdout was pending
   or Level C was in progress. They now reflect the completed, evaluated-once
   state.
4. The memo now states that P10.1's 2024 H1 slice participated in calibration-
   method selection. It is development/model-selection evidence; the locked
   P10.3 holdout is the independent final test.

## Material interpretation limits

- The result is a balancing-pressure classification study, not executable
  trading P&L. Historical publication timing prevents the strong persistence
  reference from being called decision-eligible.
- The calibrated holdout edge is small: balanced accuracy 0.352 versus 0.333
  majority and 0.329 hour-of-week. Its multiclass Brier score is worse than the
  class-frequency reference, so the probabilities have no demonstrated skill.
- The model predicts NEUTRAL for about 95% of scored holdout hours. The useful
  concentration is the small set of DOWN calls, not broad three-class accuracy.
- The two PDFs are polished frozen-blueprint/reading references dated before the
  empirical completion. The current empirical conclusion lives in the README,
  research memo and P10 evidence.
- Large raw and processed data are intentionally local and git-ignored. Their
  requests and SHA-256 values are committed, so integrity is auditable, while a
  new machine still has to retrieve or receive the data before rebuilding.

## Final assessment

The repository supports its stated conclusion. Its strongest deliverable is the
research control chain: point-in-time field classification, frozen target,
pre-registered primary hypothesis, explicit failure regimes, naive baselines,
an abstaining transparent rule, and a single closed holdout. The empirical edge
is too weak and poorly calibrated for deployment, and the project says so.
