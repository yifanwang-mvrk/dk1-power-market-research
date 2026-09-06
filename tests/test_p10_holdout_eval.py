from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.p10_holdout_eval import FROZEN_DELTA, _label_with_delta, _p7_rule, _set_holdout_state


class LabelTests(unittest.TestCase):
    def test_label_with_frozen_delta(self) -> None:
        spread = pd.Series([10.0, -10.0, 3.0, FROZEN_DELTA, -FROZEN_DELTA, np.nan])
        lab = _label_with_delta(spread, FROZEN_DELTA)
        self.assertEqual(list(lab[:5]), ["UP", "DOWN", "NEUTRAL", "NEUTRAL", "NEUTRAL"])
        self.assertTrue(pd.isna(lab.iloc[5]))


class P7RuleTests(unittest.TestCase):
    def test_p7_rule_matches_the_frozen_thresholds(self) -> None:
        df = pd.DataFrame(
            {
                "wind_revision_mwh": [400.0, -400.0, 10.0, 400.0],
                "wind_forecast_5h_mwh": [2000.0, 2000.0, 2000.0, 100.0],
                "residual_load_known_mwh": [0.0, 2500.0, 0.0, 0.0],
            }
        )
        pred = _p7_rule(df)
        self.assertEqual(pred.iloc[0], "DOWN")     # big + revision, wind not low
        self.assertEqual(pred.iloc[1], "UP")       # very tight residual load
        self.assertEqual(pred.iloc[2], "NEUTRAL")  # nothing crosses
        self.assertEqual(pred.iloc[3], "NEUTRAL")  # + revision but low wind blind spot


class ConfigWriteTests(unittest.TestCase):
    def test_set_holdout_state_only_touches_the_holdout_block(self) -> None:
        import tempfile

        original = Path("config/research_config.yaml").read_text()
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            fh.write(original)
            tmp = Path(fh.name)
        try:
            _set_holdout_state(tmp, state="evaluated", fetch_allowed=False, unlock_decision="D036")
            import yaml

            reloaded = yaml.safe_load(tmp.read_text())
            self.assertEqual(reloaded["periods"]["holdout"]["state"], "evaluated")
            self.assertIs(reloaded["periods"]["holdout"]["fetch_allowed"], False)
            self.assertEqual(reloaded["periods"]["holdout"]["start_date"], "2024-07-01")
            # everything else intact
            self.assertEqual(reloaded["neutral_band"]["numerical_delta"], 5.9956075)
            self.assertIn("level_c_model", reloaded)
            self.assertEqual(reloaded["periods"]["development"]["start_date"], "2022-01-01")
        finally:
            tmp.unlink()


class ResultTests(unittest.TestCase):
    def test_holdout_result_is_internally_consistent(self) -> None:
        r = json.loads(
            Path("research/evidence/p10_holdout/p10_3_holdout_result_2026-09-06.json").read_text()
        )
        self.assertEqual(r["holdout"], "EVALUATED_ONCE")
        dist = r["calibrated_prediction_distribution"]
        total_pred = sum(d["n"] for d in dist.values())
        self.assertEqual(total_pred, r["coverage"]["feature_complete_and_labelled"])
        # realized DOWN among all predictions must not exceed the holdout DOWN count
        realized_down = sum(
            (d["realized_shares"]["DOWN"] or 0) * d["n"] for d in dist.values()
        )
        self.assertLessEqual(realized_down, r["label_counts_holdout"]["DOWN"] + 1)


if __name__ == "__main__":
    unittest.main()
