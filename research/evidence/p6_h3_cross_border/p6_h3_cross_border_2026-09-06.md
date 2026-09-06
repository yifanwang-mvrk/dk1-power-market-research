# P6 — H3 Cross-Border and System Conditions

**Status:** P6.1 and P6.2 complete — 2026-09-06
**Scope:** development only, exploratory / descriptive (E002)
**Holdout:** LOCKED AND UNUSED

## Conclusion

**H3 CONDITIONS H2 ONLY THROUGH REALIZED FLOWS (DIAGNOSTIC); THE DECISION-ELIGIBLE DAY-AHEAD CAPACITY AND SCHEDULE DO NOT MATERIALLY MOVE THE H2 GRADIENT**

## P6.1 — cross-border conditioning variables

Usable borders: ['de', 'dk2', 'nl', 'no2', 'se3'] (GB excluded — all
day-ahead fields null, P1.4).

- `import_headroom_mw` = Σ positive import capacity into DK1.
- `export_headroom_mw` = Σ magnitude of the (negative-stored) export capacity;
  166 hours have an
  anomalous positive export-capacity record and are treated as zero available
  export.
- `net_scheduled_exchange_da_mw` = Σ day-ahead scheduled exchange
  (positive = net import into DK1). All three are decision-eligible: published
  day-ahead, before the delivery-hour cutoff (D024 / D025).
- `realized_net_import_mwh` = Σ settled cross-border flow
  (['no', 'se', 'ge', 'nl', 'great_belt']); **diagnostic only**.

Coverage: eligible conditions available for
21,887 /
21,887 hours; realized flow for
21,887.

## P6.2 — does H3 condition the H2 gradient?

Metric: the H2 wind-revision gradient (Q5−Q1 spread in `P(DOWN) − P(UP)`)
computed separately inside each tercile of a cross-border variable. If H3
conditions H2, the gradient is materially steeper when the export direction is
congested.

### Decision-eligible

### Export headroom

Congested tercile: `T1_low`. Predicted: steeper H2 DOWN-gradient when the export direction is congested.

| Tercile | Hours | H2 gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
| T1_low | 7,213 | +1.00 | +0.168 |
| T2_mid | 7,453 | +1.00 | +0.217 |
| T3_high | 6,948 | +0.90 | +0.180 |

Gradient spread, congested − open: `-0.012` (threshold `> 0.05`) → conditions H2: **False**

### Net day-ahead scheduled exchange

Congested tercile: `T1_low`. Predicted: steeper H2 DOWN-gradient when the export direction is congested.

| Tercile | Hours | H2 gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
| T1_low | 7,205 | +0.90 | +0.124 |
| T2_mid | 7,205 | +1.00 | +0.269 |
| T3_high | 7,204 | +0.90 | +0.171 |

Gradient spread, congested − open: `-0.047` (threshold `> 0.05`) → conditions H2: **False**


### Diagnostic (realized flow — not decision-eligible)

### Realized net import

Congested tercile: `T3_high`. Predicted: steeper H2 DOWN-gradient when the export direction is congested.

| Tercile | Hours | H2 gradient Spearman | Q5−Q1 spread |
|---|---:|---:|---:|
| T1_low | 7,205 | +0.90 | +0.175 |
| T2_mid | 7,205 | +1.00 | +0.212 |
| T3_high | 7,204 | +1.00 | +0.231 |

Gradient spread, congested − open: `+0.056` (threshold `> 0.05`) → conditions H2: **True**


## Chart

`p6_h3_gradient_by_crossborder_2026-09-06.png` — H2 gradient by conditioning
tercile; a flat profile means H3 does not condition H2.

## Limitations

In-sample / descriptive. Export-capacity sign convention is imperfect (166 anomalous hours). Countertrade (partial period from 2023-04-18) and border-specific flow modelling are not included; a proper H3 model is later work. GB is excluded (null day-ahead fields).
