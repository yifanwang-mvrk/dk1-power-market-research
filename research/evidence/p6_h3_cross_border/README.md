# P6 — H3 Cross-Border and System Conditions Evidence

**Status:** P6.1 and P6.2 complete 2026-09-06 — **diagnostic conditioning only**;
Level B B3 done
**Holdout:** LOCKED AND UNUSED

`src/p6_cross_border.py` builds decision-eligible cross-border conditioning
variables and tests whether the H2 wind-revision gradient changes with them.
Tests: `tests/test_p6_cross_border.py`. Quality gate:
`p6_quality_report_2026-09-06.json` (7/7). Exploratory / descriptive (E002); the
border subset, sign conventions and tercile scheme were declared before crossing
outcomes.

## P6.1 — conditioning variables

Usable borders: DE, DK2, NL, NO2, SE3 (GB excluded — all day-ahead fields null,
P1.4). All decision-eligible, published day-ahead (D024 / D025):

- `import_headroom_mw` = Σ positive import capacity into DK1
- `export_headroom_mw` = Σ magnitude of the negative-stored export capacity; 166
  hours with an anomalous positive export-capacity record are treated as zero
  available export and flagged
- `net_scheduled_exchange_da_mw` = Σ day-ahead scheduled exchange (positive = net
  import into DK1)

`realized_net_import_mwh` (settled flow across NO, SE, GE, NL, Great Belt) is
`diagnostic_only`.

## P6.2 — does H3 condition the H2 gradient?

The H2 wind-revision gradient (Q5−Q1 spread in `P(DOWN) − P(UP)`) computed inside
each tercile of a cross-border variable.

| Conditioning variable | Class | Gradient: congested − open tercile | Conditions H2 (> 0.05)? |
|---|---|---:|---|
| Export headroom | eligible | −0.012 | No |
| Net day-ahead scheduled exchange | eligible | −0.047 | No |
| Realized net import | diagnostic | +0.056 | Weakly (diagnostic) |

**Conclusion: diagnostic conditioning only.** The two decision-eligible variables
show a mid-tercile hump — a noise signature. Interconnector capacity barely
varies hour to hour (export headroom Q20/Q80 ≈ 4.7 / 5.8 GW). Only the realized
net-import flow (unknown at decision time) shows a weak steepening when DK1 ends
up short — consistent with a congested export direction trapping a wind surplus.
**No decision-eligible H3 conditioning signal.** Decision D032.

## Next steps

| Step | Action |
|---|---|
| P7 | Transparent signal engine: H2 wind revision + H1-B residual-load proxy; no H3 input |
| P9 | Short research memo |
