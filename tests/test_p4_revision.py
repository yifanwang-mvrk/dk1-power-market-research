from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.p4_revision import (
    FORECAST_1H,
    FORECAST_5H,
    _bucketize,
    build_revisions,
    near_zero_bands,
    normalization_floor,
)


def _frame(rows: list[dict[str, float | None]]) -> pd.DataFrame:
    base = {col: [] for col in list(FORECAST_5H.values()) + list(FORECAST_1H.values())}
    for row in rows:
        for col in base:
            base[col].append(row.get(col))
    return pd.DataFrame(base)


class RevisionTests(unittest.TestCase):
    def test_per_type_revision_needs_both_horizons(self) -> None:
        frame = _frame(
            [
                {
                    FORECAST_5H["offshore_wind"]: 100.0,
                    FORECAST_1H["offshore_wind"]: 140.0,
                    FORECAST_5H["onshore_wind"]: 200.0,
                    FORECAST_1H["onshore_wind"]: 180.0,
                    FORECAST_5H["solar"]: 0.0,
                    FORECAST_1H["solar"]: 0.0,
                },
                {
                    FORECAST_5H["offshore_wind"]: 100.0,
                    FORECAST_1H["offshore_wind"]: None,
                    FORECAST_5H["onshore_wind"]: 200.0,
                    FORECAST_1H["onshore_wind"]: 210.0,
                    FORECAST_5H["solar"]: 5.0,
                    FORECAST_1H["solar"]: 9.0,
                },
            ]
        )
        result = build_revisions(frame)
        self.assertEqual(result.loc[0, "revision_offshore_wind_mwh"], 40.0)
        self.assertEqual(result.loc[0, "revision_onshore_wind_mwh"], -20.0)
        self.assertEqual(result.loc[0, "wind_revision_mwh"], 20.0)
        self.assertTrue(pd.isna(result.loc[1, "revision_offshore_wind_mwh"]))
        self.assertTrue(pd.isna(result.loc[1, "wind_revision_mwh"]))
        self.assertFalse(result.loc[1, "wind_revision_available"])

    def test_five_h_equals_one_h_and_solar_both_positive_flags(self) -> None:
        frame = _frame(
            [
                {
                    FORECAST_5H["offshore_wind"]: 100.0,
                    FORECAST_1H["offshore_wind"]: 100.0,
                    FORECAST_5H["onshore_wind"]: 200.0,
                    FORECAST_1H["onshore_wind"]: 200.0,
                    FORECAST_5H["solar"]: 0.0,
                    FORECAST_1H["solar"]: 0.0,
                },
                {
                    FORECAST_5H["offshore_wind"]: 100.0,
                    FORECAST_1H["offshore_wind"]: 130.0,
                    FORECAST_5H["onshore_wind"]: 200.0,
                    FORECAST_1H["onshore_wind"]: 205.0,
                    FORECAST_5H["solar"]: 5.0,
                    FORECAST_1H["solar"]: 12.0,
                },
            ]
        )
        result = build_revisions(frame)
        self.assertTrue(result.loc[0, "wind_revision_5h_eq_1h"])
        self.assertTrue(result.loc[0, "revision_solar_5h_eq_1h"])
        self.assertFalse(result.loc[0, "solar_both_horizons_positive"])
        self.assertFalse(result.loc[1, "wind_revision_5h_eq_1h"])
        self.assertTrue(result.loc[1, "solar_both_horizons_positive"])


class BucketTests(unittest.TestCase):
    def test_signed_quantile_edges_and_assignment(self) -> None:
        values = pd.Series([float(x) for x in range(-50, 51)])  # -50..50
        bucket, edges, note = _bucketize(values, (0.20, 0.40, 0.60, 0.80))
        self.assertEqual(len(edges), 4)
        self.assertEqual(edges, sorted(edges))
        self.assertEqual(note, "edges strictly increasing")
        self.assertEqual(int(bucket.iloc[0]), 1)   # -50 -> most negative bucket
        self.assertEqual(int(bucket.iloc[-1]), 5)  # +50 -> most positive bucket
        self.assertEqual(sorted(bucket.dropna().unique().tolist()), [1, 2, 3, 4, 5])

    def test_duplicate_edges_are_reported(self) -> None:
        values = pd.Series([0.0] * 80 + [float(x) for x in range(1, 21)])
        _bucket, edges, note = _bucketize(values, (0.20, 0.40, 0.60, 0.80))
        self.assertLess(len(edges), 4)
        self.assertIn("collapsed", note)


class HelperTests(unittest.TestCase):
    def test_near_zero_bands_count_exact_and_within(self) -> None:
        revision = pd.Series([0.0, 0.5, -0.9, 3.0, -20.0, np.nan])
        bands = near_zero_bands(revision)
        self.assertEqual(bands["exactly_zero"]["count"], 1)
        self.assertEqual(bands["abs_le_1_mwh"]["count"], 3)
        self.assertEqual(bands["abs_le_5_mwh"]["count"], 4)

    def test_normalization_floor_uses_positive_values_only(self) -> None:
        forecast = pd.Series([0.0, -1.0, 10.0, 20.0, 30.0, 40.0, np.nan])
        floor = normalization_floor(forecast)
        self.assertGreater(floor, 0.0)
        self.assertLessEqual(floor, 20.0)


if __name__ == "__main__":
    unittest.main()
