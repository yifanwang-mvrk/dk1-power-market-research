# P1.3 RegulatingBalancePowerdata Evidence

This directory preserves the official-source evidence used to select the
historical DK1 hourly balancing outcome for the declared development period.

## Evidence files

- `metadata_RegulatingBalancePowerdata_2026-09-06.json`: official metadata for
  the discontinued hourly historical dataset.
- `candidate_metadata_ImbalancePrice_2026-09-06.json`: official metadata for
  the active 15-minute successor. Its 2025 start is outside the declared
  development period, so it is not mixed into the historical extract.
- `sample_dk1_2024-01-15.json`: one complete DK1 development-day sample used to
  inspect field behavior.
- `dst_window_dk1_2022-10-30.json`: bounded official API response confirming
  that five of six consecutive UTC hours are returned around the identified
  2022 fall-back gap.
- `retrieval_manifest_2026-09-06.json`: source URLs, hashes and holdout-control
  declarations for the preserved official files.
- `development_extract_manifest_2026-09-06.json`: provenance and hash for the
  ignored full development extract under `data/raw/p1_3_validation/`.
- `development_validation_2026-09-06.json` and `.md`: complete development
  coverage, key, target-price, DST, successor and handling validation.

## Decision established

For the hourly 2022-01-01 through 2024-06-30 development period, use DK1
`RegulatingBalancePowerdata.ImbalancePriceEUR` as `P_Balancing,t` in EUR/MWh.
It is an ex-post outcome. `BalancingPowerPriceUpEUR` and
`BalancingPowerPriceDownEUR` remain audit components and must not be selected
after observing which direction gives a preferred research result.

The Nordic single-price and single-position model went live on 2021-11-01,
before the development period:
<https://nordicbalancingmodel.net/confirmation-of-go-live-of-single-price-and-single-position-on-1-november-2021/>.

Energi Data Service states that published data are licensed under CC BY 4.0
and recommends attribution to Energinet:
<https://www.energidataservice.dk/support-service>.

## Conditional-pass limitation

The official development extract contains 21,886 of 21,887 expected DK1
delivery hours. The absent row is `2022-10-30T00:00:00Z`, the first repeated
local 02:00 hour on the fall-back day. The row must remain missing; it must not
be created or filled with zero.

All returned rows contain `ImbalancePriceEUR`, and every value matches the
official Up price, Down price or both. The legacy metadata reports update
frequency as N/A and does not provide an exact historical publication delay.
That limitation remains under I03/P2.3 because it affects when a lagged outcome
could become decision eligible.

## Scope control

No locked-holdout outcome row was requested, saved or inspected. The target is
a balancing-pressure research outcome and must not be presented as executable
trading P&L.
