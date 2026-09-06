from __future__ import annotations

import unittest

import pandas as pd

from src.p3_target import (
    assign_labels,
    baseline_report,
    build_spread,
    calculate_delta,
)


class SpreadTests(unittest.TestCase):
    def test_same_row_eur_spread_and_missing_are_preserved(self) -> None:
        frame = pd.DataFrame(
            {
                "spot_price_eur_mwh": [50.0, 60.0],
                "imbalance_price_eur_mwh": [42.0, None],
            }
        )
        result = build_spread(frame)
        self.assertEqual(result.loc[0, "balancing_spread_eur_mwh"], -8.0)
        self.assertTrue(pd.isna(result.loc[1, "balancing_spread_eur_mwh"]))


class DeltaTests(unittest.TestCase):
    def test_q25_excludes_missing_and_observed_zero(self) -> None:
        spread = pd.Series([None, 0.0, -2.0, 4.0, -8.0, 10.0])
        result = calculate_delta(spread)
        self.assertEqual(result["valid_spreads"], 5)
        self.assertEqual(result["zero_spreads_excluded"], 1)
        self.assertEqual(result["nonzero_absolute_spreads"], 4)
        self.assertAlmostEqual(result["delta_eur_mwh"], 3.5)


class LabelTests(unittest.TestCase):
    def test_boundaries_zero_and_missing_follow_frozen_rules(self) -> None:
        frame = pd.DataFrame(
            {
                "balancing_spread_eur_mwh": [
                    5.1,
                    5.0,
                    0.0,
                    -5.0,
                    -5.1,
                    None,
                ]
            }
        )
        result = assign_labels(frame, 5.0)
        self.assertEqual(
            result["target_label"].tolist(),
            ["UP", "NEUTRAL", "NEUTRAL", "NEUTRAL", "DOWN", pd.NA],
        )
        self.assertFalse(result.loc[5, "target_is_valid"])


class BaselineTests(unittest.TestCase):
    def test_persistence_requires_consecutive_valid_labels(self) -> None:
        frame = pd.DataFrame(
            {
                "delivery_start_utc": pd.to_datetime(
                    [
                        "2024-01-01T00:00:00Z",
                        "2024-01-01T01:00:00Z",
                        "2024-01-01T02:00:00Z",
                        "2024-01-01T03:00:00Z",
                        "2024-01-01T04:00:00Z",
                    ]
                ),
                "target_label": pd.Series(
                    ["UP", "UP", pd.NA, "DOWN", "DOWN"], dtype="string"
                ),
            }
        )
        report = baseline_report(frame)
        self.assertEqual(report["persistence"]["eligible_pairs"], 2)
        self.assertEqual(report["persistence"]["correct"], 2)
        self.assertFalse(report["persistence"]["decision_feature_eligible"])


if __name__ == "__main__":
    unittest.main()
