"""Core time-spine tests for the P2 data pipeline."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.p2_pipeline import expected_time_base, load_config


ROOT = Path(__file__).resolve().parents[1]


class TimeSpineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(ROOT)
        cls.frame = expected_time_base(cls.config)

    def test_development_has_expected_real_hours(self):
        self.assertEqual(len(self.frame), 21887)
        self.assertTrue(self.frame["delivery_start_utc"].is_unique)

    def test_dst_fallback_hours_are_not_collapsed(self):
        repeated = self.frame[
            self.frame["local_wall_time"].eq("2022-10-30T02:00:00")
        ]
        self.assertEqual(len(repeated), 2)
        self.assertEqual(repeated["local_hour_occurrence"].tolist(), [1, 2])
        self.assertEqual(repeated["delivery_start_utc"].nunique(), 2)

    def test_holdout_is_absent(self):
        self.assertEqual(self.frame["local_date"].max(), "2024-06-30")
        self.assertFalse((self.frame["local_date"] >= "2024-07-01").any())


if __name__ == "__main__":
    unittest.main()
