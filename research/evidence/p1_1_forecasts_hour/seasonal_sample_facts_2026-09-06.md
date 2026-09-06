# Forecasts_Hour Seasonal and Known-Gap Sample Facts

All samples are restricted to DK1 and dates inside the development period.
The known-gap sample tests the official missing-data notice.

| Sample | Records | Hours | Duplicate key rows | Solar 5h zero | Solar 1h zero | Either zero |
|---|---:|---:|---:|---:|---:|---:|
| sample_dk1_2024-01-15_2024-01-16.json | 72 | 24 | 0 | 7 | 7 | 7 |
| sample_dk1_2024-04-05_2024-04-06.json | 72 | 24 | 0 | 7 | 8 | 8 |
| sample_dk1_2024-06-15_2024-06-16.json | 72 | 24 | 0 | 0 | 0 | 0 |
| sample_dk1_2024-04-13_2024-04-14.json | 0 | 0 | 0 | n/a | n/a | n/a |

## Solar zero-pair hours in Danish local time

- `sample_dk1_2024-01-15_2024-01-16.json`: 01:00, 02:00, 03:00, 21:00, 22:00, 23:00, 00:00
- `sample_dk1_2024-04-05_2024-04-06.json`: 02:00, 03:00, 04:00, 21:00, 22:00, 23:00, 00:00, 01:00
- `sample_dk1_2024-06-15_2024-06-16.json`: none
- `sample_dk1_2024-04-13_2024-04-14.json`: none

## Interpretation boundary

These observations do not determine whether a zero is a valid zero forecast or an unavailable forecast encoded as zero.
No point-in-time eligibility decision is made by this report.
