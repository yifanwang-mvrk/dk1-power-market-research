# Data Dictionary

**Project:** DK1 Short-Term Power Market Research
**Status:** Initialized; official source validation not started
**Last updated:** 2026-09-05

## Field Registry

| Dataset | Field | Business Meaning | Unit | Time Meaning | PIT Class | Evidence Status |
|---|---|---|---|---|---|---|
| Pending | Pending | Pending official source validation | Pending | Pending | Pending | Not validated |

## Point-in-Time Classes

- `decision_eligible`: available at the simulated decision time
- `diagnostic_only`: useful for explanation but unavailable for the decision
- `outcome`: known only after the delivery period

## Registration Rules

- Do not classify a field as decision eligible only because it appears in historical data.
- Record the official definition, unit and timestamp meaning.
- Use `HourUTC` as the canonical join key unless source validation establishes otherwise.
- Retain Danish local time for interpretation and daylight-saving checks.
- Record missing values and duplicate keys explicitly.
- Do not convert missing values to zero without documented evidence.
- Do not access or register fields from the locked holdout before its formal unlock.
