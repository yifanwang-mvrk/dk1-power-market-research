# P1.4 Development Validation

**Status:** PASS — source eligibility inventory established

## Scope control

- Development boundary: 2022-01-01 through 2024-06-30 (local dates)
- Expected DK1 delivery hours: 21,887
- Locked holdout rows inspected: 0
- Missing values are preserved; no source-defined null is converted to zero

## Actual fundamentals

- Source: `ProductionConsumptionSettlement`; status `PASS`; eligibility `diagnostic_only`
- Rows / unique hours: 21,887 / 21,887
- Complete derived residual-load rows: 21,887
- Negative residual-load hours: 5,974 (27.29%)
- Formula: gross consumption minus total actual wind minus total actual solar
- Meaning: suitable for explaining historical system tightness, not for a pre-delivery decision feature

## Cross-border and system sources

- `Transmissionlines`: `CONDITIONAL PASS`; day-ahead capacities and day-ahead schedules are decision-eligible candidates pending P2.3 cutoff mapping
- Final intraday schedule and physical exchange fields are diagnostic only
- Connections observed: DE, DK2, GB, NL, NO2, SE3
- Positive `ExportCapacity` rows preserved: 358
- GB rows with unavailable legacy day-ahead schedule: 5,374
- `CountertradeIntraday`: `CONDITIONAL PASS`; partial-period conditional candidate
- Countertrade rows available at least one hour before delivery: 7,447 / 7,751
- The 2025 successor is unavailable for the development period

## Eligibility conclusion

P1.4 is complete because every required research role now has a selected source, a conditional candidate, or an evidenced unavailable status. Exact row-level cutoff enforcement remains an implementation task in P2.3; H1-B proxy selection remains a registered P5.2 question. These are downstream gates rather than missing P1.4 inventory work.

The holdout remained locked and unused. No executable trading P&L is claimed.
