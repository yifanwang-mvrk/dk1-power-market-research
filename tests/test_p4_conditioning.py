from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.p4_conditioning import (
    HOUR_BLOCKS,
    SEASON,
    _score,
    gradient_for,
)


class DeclaredBinTests(unittest.TestCase):
    def test_season_map_covers_twelve_months(self) -> None:
        self.assertEqual(sorted(SEASON), list(range(1, 13)))
        self.assertEqual(set(SEASON.values()), {"winter", "spring", "summer", "autumn"})

    def test_hour_blocks_partition_the_day(self) -> None:
        covered = []
        for lo, hi, _name in HOUR_BLOCKS:
            covered.extend(range(lo, hi + 1))
        self.assertEqual(sorted(covered), list(range(24)))


class GradientTests(unittest.TestCase):
    def test_monotone_down_gradient_is_directionally_consistent(self) -> None:
        rows = []
        # bucket 1 -> mostly UP, bucket 5 -> mostly DOWN
        mix = {1: ("UP", 7), 2: ("UP", 6), 3: ("NEUTRAL", 5), 4: ("DOWN", 6), 5: ("DOWN", 8)}
        for bucket, (lab, k) in mix.items():
            for _ in range(300):
                rows.append({"wind_revision_quintile": bucket, "target_label": lab if _ % 10 < k else "NEUTRAL"})
        frame = pd.DataFrame(rows)
        rep = gradient_for(frame, "wind_revision_quintile")
        self.assertFalse(rep["insufficient"])
        self.assertGreaterEqual(rep["gradient_spearman"], 0.8)
        self.assertTrue(rep["directionally_consistent"])
        self.assertGreater(rep["extreme_bucket_spread"], 0)

    def test_small_sample_flagged_insufficient(self) -> None:
        frame = pd.DataFrame(
            {"wind_revision_quintile": [1, 2, 3], "target_label": ["UP", "DOWN", "NEUTRAL"]}
        )
        self.assertTrue(gradient_for(frame, "wind_revision_quintile")["insufficient"])


class ScoreTests(unittest.TestCase):
    def test_score_reports_balanced_accuracy(self) -> None:
        y_true = pd.Series(["UP", "DOWN", "NEUTRAL", "UP", "DOWN", "NEUTRAL"])
        out = _score(y_true, y_true)
        self.assertAlmostEqual(out["balanced_accuracy"], 1.0)
        self.assertAlmostEqual(out["macro_f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
