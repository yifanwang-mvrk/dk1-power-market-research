# P1.1 Forecasts_Hour Evidence

This directory preserves official-source evidence used to validate the
`Forecasts_Hour` dataset. Interpretive conclusions remain provisional until
the metadata and development-period samples have been reviewed.

## Evidence files

- `metadata_2026-09-05.json`: raw official dataset metadata.
- `api_query_contract_2026-09-05.json`: official query-parameter definitions
  extracted from the Energi Data Service public Swagger specification.
- `retrieval_manifest_2026-09-05.json`: retrieval URLs, timestamps and SHA-256
  hashes for the preserved evidence.
- `sample_dk1_*.json`: raw, date-bounded DK1 development samples.
- `sample_profile_*.json` and `.md`: one-day structural profiles.
- `seasonal_sample_facts_2026-09-06.json` and `.md`: factual comparison of
  winter, spring, summer and the official known-gap sample.
- `retrieval_manifest_2026-09-06.json`: provenance and hashes for the added
  official samples.
- `development_validation_2026-09-06.json` and `.md`: complete development
  coverage, pairing, DST, value-quality and versioning validation.
- `development_extract_manifest_2026-09-06.json`: provenance and hash for the
  ignored full development extract stored under `data/raw/p1_1_validation/`.

## Final P1.1 disposition

`Forecasts_Hour` received a **CONDITIONAL PASS** for same-hour DK1 5h-to-1h
forecast-revision research. The dataset supports fixed-horizon snapshots with
documented missingness, zero-value and DST rules. It does not support a claim
of complete tick-by-tick forecast-vintage reconstruction. The exact simulated
decision cutoff remains to be frozen in P2.3.

## Scope control

All data samples in P1.1 must use explicit dates inside the development period.
The locked holdout remains unused.
