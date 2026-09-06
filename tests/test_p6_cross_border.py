from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.p6_cross_border import (
    REALIZED_BORDERS,
    USABLE_BORDERS,
    _terciles,
    build_cross_border,
    h2_gradient,
)


def _cross_border_row(**over: float) -> dict[str, float]:
    row: dict[str, float] = {}
    for b in USABLE_BORDERS:
        row[f"transmission_import_capacity_{b}"] = 500.0
        row[f"transmission_export_capacity_{b}"] = -500.0
        row[f"transmission_scheduled_exchange_day_ahead_{b}"] = -100.0
    for b in REALIZED_BORDERS:
        row[f"actual_exchange_{b}_mwh"] = -50.0
    row.update(over)
    return row


class BuildTests(unittest.TestCase):
    def test_headroom_signs_and_positive_export_flag(self) -> None:
        normal = _cross_border_row()
        anomaly = _cross_border_row(**{f"transmission_export_capacity_{USABLE_BORDERS[0]}": 300.0})
        frame = pd.DataFrame([normal, anomaly])
        out, meta = build_cross_border(frame)
        # 5 borders x 500 import capacity
        self.assertEqual(out.loc[0, "import_headroom_mw"], 2500.0)
        # 5 borders x |-500| export magnitude
        self.assertEqual(out.loc[0, "export_headroom_mw"], 2500.0)
        # anomaly row: one border positive -> counts as zero export there
        self.assertEqual(out.loc[1, "export_headroom_mw"], 2000.0)
        self.assertFalse(bool(out.loc[0, "any_positive_export_capacity"]))
        self.assertTrue(bool(out.loc[1, "any_positive_export_capacity"]))
        self.assertEqual(out.loc[0, "net_scheduled_exchange_da_mw"], -500.0)
        self.assertEqual(out.loc[0, "realized_net_import_mwh"], -250.0)
        self.assertTrue(meta["realized_classification"].startswith("diagnostic"))
        self.assertNotIn("gb", meta["usable_borders"])


class HelperTests(unittest.TestCase):
    def test_terciles_three_labels(self) -> None:
        bucket, edges = _terciles(pd.Series(np.arange(300, dtype=float)))
        self.assertEqual(len(edges), 2)
        self.assertEqual(set(bucket.dropna().unique()), {"T1_low", "T2_mid", "T3_high"})

    def test_h2_gradient_small_sample_is_flagged(self) -> None:
        frame = pd.DataFrame(
            {"wind_revision_quintile": [1, 2, 3], "target_label": ["UP", "DOWN", "NEUTRAL"]}
        )
        self.assertTrue(h2_gradient(frame)["insufficient"])

    def test_h2_gradient_monotone_down(self) -> None:
        rows = []
        for bucket in range(1, 6):
            down = 0.2 + 0.05 * bucket
            for i in range(600):
                lab = "DOWN" if i / 600 < down else ("UP" if i / 600 < down + 0.2 else "NEUTRAL")
                rows.append({"wind_revision_quintile": bucket, "target_label": lab})
        rep = h2_gradient(pd.DataFrame(rows))
        self.assertFalse(rep["insufficient"])
        self.assertGreaterEqual(rep["gradient_spearman"], 0.8)
        self.assertGreater(rep["q5_minus_q1_spread"], 0)


if __name__ == "__main__":
    unittest.main()
