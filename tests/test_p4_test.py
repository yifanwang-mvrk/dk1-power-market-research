from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.p4_test import (
    LABEL_SCORE,
    PREDICTED_SPREAD_SIGN,
    spearman_with_ci,
    transparent_rule,
)


class RuleTests(unittest.TestCase):
    def test_symmetric_threshold_rule(self) -> None:
        revision = pd.Series([200.0, -200.0, 10.0, 128.083, -128.083, np.nan])
        pred = transparent_rule(revision, 128.083)
        self.assertEqual(pred.iloc[0], "DOWN")   # large positive revision -> DOWN
        self.assertEqual(pred.iloc[1], "UP")     # large negative revision -> UP
        self.assertEqual(pred.iloc[2], "NEUTRAL")
        self.assertEqual(pred.iloc[3], "NEUTRAL")  # exactly c is not > c
        self.assertEqual(pred.iloc[4], "NEUTRAL")
        self.assertTrue(pd.isna(pred.iloc[5]))


class ScoreTests(unittest.TestCase):
    def test_label_score_mapping(self) -> None:
        self.assertEqual(LABEL_SCORE, {"UP": 1, "NEUTRAL": 0, "DOWN": -1})

    def test_predicted_sign_is_negative(self) -> None:
        # positive wind revision -> looser system -> lower (more negative) spread
        self.assertEqual(PREDICTED_SPREAD_SIGN, -1)


class SpearmanTests(unittest.TestCase):
    def test_negative_monotone_relationship_is_detected(self) -> None:
        x = pd.Series(np.arange(400, dtype=float))
        y = pd.Series(-np.arange(400, dtype=float) + np.sin(np.arange(400)))
        out = spearman_with_ci(x, y, "x vs y")
        self.assertLess(out["spearman_rho"], -0.9)
        self.assertTrue(out["ci_excludes_zero"])
        self.assertEqual(out["observed_sign"], -1)
        self.assertTrue(out["sign_matches_prediction"])
        self.assertTrue(out["association_supported"])

    def test_zero_relationship_ci_contains_zero(self) -> None:
        rng = np.random.default_rng(0)
        x = pd.Series(rng.normal(size=600))
        y = pd.Series(rng.normal(size=600))
        out = spearman_with_ci(x, y, "noise")
        self.assertFalse(out["association_supported"])


if __name__ == "__main__":
    unittest.main()
