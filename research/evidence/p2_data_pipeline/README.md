# P2 Data Pipeline Evidence

**Status:** PASS — P2.1 through P2.5 completed on 2026-09-06

## What this phase proves

The six P1-preserved Energinet development responses can be acquired through a
date-bounded client, traced by immutable hashes, normalized to one UTC delivery
key, joined to a `21,887`-hour DK1 base table,
and checked without requesting or processing the locked holdout.

## Step evidence

- **P2.1:** `p2_1_sample_manifest_2026-09-06.json`, the saved bounded sample,
  client guard-rail tests and explicit 429/invalid-response handling
- **P2.2:** `raw_provenance_2026-09-06.json`; every raw hash still matches its
  P1 manifest
- **P2.3:** `availability_contract_2026-09-06.json`; UTC/local/DST mappings and
  the last-pre-delivery information cutoff are explicit
- **P2.4:** `join_manifest_2026-09-06.json` and
  `hourly_base_audit_sample_2026-09-06.csv`; the processed parquet remains
  local and git-ignored
- **P2.5:** `quality_report_2026-09-06.md` and JSON

## Final structural facts

- Hourly base: `21,887` unique DK1 delivery hours
- Spot-price gaps: `0`
- Balancing-price gaps: `1`; the known
  `2022-10-30T00:00:00Z` gap remains null
- Same-hour 5h/1h pairs: offshore
  `21,667`, onshore
  `21,637`, solar
  `21,664`
- Holdout rows: `0`

P2 deliberately does not calculate the balancing spread, neutral band, labels
or 5h-to-1h revisions. Those transformations begin in P3 and P4 so the data
foundation remains auditable.
