# P1.2 Elspotprices Evidence

This directory preserves the official-source evidence used to validate the
DK1 day-ahead reference price for the declared development period.

## Evidence files

- `metadata_2026-09-06.json`: raw official metadata for the legacy
  `Elspotprices` dataset.
- `sample_dk1_2024-01-15_2024-01-16_utc.json`: bounded official DK1 sample used
  to confirm the returned schema and hourly row grain.
- `retrieval_manifest_2026-09-06.json`: retrieval URLs, timestamp, hashes and
  holdout-control declarations for the preserved official files.
- `development_extract_manifest_2026-09-06.json`: provenance and hash for the
  ignored full development extract under `data/raw/p1_2_validation/`.
- `development_validation_2026-09-06.json` and `.md`: complete development
  coverage, key, price-quality, DST and field-selection validation.

The API query semantics are shared with P1.1 and preserved in
`../p1_1_forecasts_hour/api_query_contract_2026-09-05.json`.

Energi Data Service states that its published data is licensed under CC BY
4.0 and recommends the attribution `Source: Energinet
(www.energidataservice.dk)`. See the official support page:
<https://www.energidataservice.dk/support-service>.

## P1.2 completion condition

P1.2 passes only if the declared development period has an official DK1
day-ahead price field with a documented unit, a stable delivery-hour key, no
unresolved duplicate-key conflict and no holdout access. Missing prices, if
found, must remain missing rather than being converted to zero.

## Scope control

The legacy `Elspotprices` dataset is discontinued after 2025-09-30 and points
users to `DayAheadPrices` for later data. This does not change the declared
2022-01-01 through 2024-06-30 development period, but any future extension
across the 2025 market-time-unit change requires a separate migration check.
