from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.p7_signal_engine import build_signal


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    n = len(rows)
    base = pd.DataFrame(
        {
            "delivery_start_utc": pd.date_range("2022-06-01", periods=n, freq="7D", tz="UTC"),
            "local_weekday": ["Wednesday"] * n,
            "local_hour": [12] * n,
            "actual_gross_consumption_mwh": [3000.0] * n,
            "forecast_5_hour_offshore_wind_mwh_per_hour": [1500.0] * n,
            "forecast_5_hour_onshore_wind_mwh_per_hour": [1500.0] * n,
            "forecast_5_hour_solar_mwh_per_hour": [200.0] * n,
            "wind_revision_mwh": [0.0] * n,
            "wind_revision_available": [True] * n,
        }
    )
    for i, over in enumerate(rows):
        for k, v in over.items():
            base.loc[i, k] = v
    return base


class SignalRuleTests(unittest.TestCase):
    def test_h2_only_emits_down_and_respects_low_wind_blind_spot(self) -> None:
        # many weak rows so the frame's own Q80 of abs(revision) lands ~2100
        frame = _frame(
            [
                {"wind_revision_mwh": 3000.0},  # big positive revision, wind not low -> DOWN
                {"wind_revision_mwh": -2000.0},  # negative revision -> H2 stays silent (no UP)
                {
                    "wind_revision_mwh": 2500.0,
                    "forecast_5_hour_offshore_wind_mwh_per_hour": 100.0,
                    "forecast_5_hour_onshore_wind_mwh_per_hour": 100.0,
                },  # big positive revision but low wind -> blind spot -> silent
                {"wind_revision_mwh": 20.0},
                {"wind_revision_mwh": -30.0},
                {"wind_revision_mwh": 40.0},
                {"wind_revision_mwh": 10.0},
                {"wind_revision_mwh": 15.0},
                {"wind_revision_mwh": 25.0},
                {"wind_revision_mwh": 35.0},
            ]
        )
        out, rules = build_signal(frame)
        self.assertLess(rules["thresholds_pre_declared"]["h2_strong_abs_revision_cut_mwh"], 3000.0)
        self.assertEqual(out.loc[0, "signal"], "DOWN PRESSURE")
        self.assertEqual(out.loc[0, "signal_confidence"], "MEDIUM")
        self.assertEqual(out.loc[1, "signal"], "NO TRADE")
        self.assertEqual(out.loc[2, "signal"], "NO TRADE")

    def test_missing_input_is_no_trade(self) -> None:
        frame = _frame([{"wind_revision_available": False, "wind_revision_mwh": np.nan}] * 4)
        out, _ = build_signal(frame)
        self.assertTrue((out["signal"] == "NO TRADE").all())

    def test_signal_values_are_the_frozen_set(self) -> None:
        frame = _frame([{"wind_revision_mwh": v} for v in (-900, -100, 0, 100, 900)])
        out, _ = build_signal(frame)
        self.assertTrue(set(out["signal"]).issubset({"UP PRESSURE", "DOWN PRESSURE", "NO TRADE"}))
        self.assertEqual(
            set(out["signal_predicted_label"].dropna()),
            set(out["signal"].map({"UP PRESSURE": "UP", "DOWN PRESSURE": "DOWN", "NO TRADE": "NEUTRAL"}).dropna()),
        )


if __name__ == "__main__":
    unittest.main()
