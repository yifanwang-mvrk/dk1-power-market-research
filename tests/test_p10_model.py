from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.p10_model import (
    CALIBRATION_END_LOCAL,
    LOW_WIND_CUT_MWH,
    TRAIN_END_LOCAL,
    _multiclass_brier,
    _split_masks,
    build_features,
)


def _base(n: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "delivery_start_utc": pd.date_range("2022-01-01", periods=n, freq="30D", tz="UTC"),
            "local_date": pd.date_range("2022-01-01", periods=n, freq="30D").astype(str),
            "local_hour": list(range(24)) + list(range(n - 24)),
            "local_weekday": (["Monday", "Saturday"] * n)[:n],
            "actual_gross_consumption_mwh": np.linspace(2000, 4000, n),
            "forecast_5_hour_offshore_wind_mwh_per_hour": np.linspace(50, 1500, n),
            "forecast_5_hour_onshore_wind_mwh_per_hour": np.linspace(50, 1500, n),
            "forecast_5_hour_solar_mwh_per_hour": np.full(n, 100.0),
            "wind_revision_mwh": np.linspace(-300, 300, n),
            "solar_revision_mwh": np.zeros(n),
            "wind_revision_available": np.full(n, True),
            "target_label": (["UP", "DOWN", "NEUTRAL"] * n)[:n],
        }
    )


class FeatureTests(unittest.TestCase):
    def test_cyclical_and_low_wind_interaction(self) -> None:
        df = build_features(_base())
        # cyclical encodings are bounded
        self.assertTrue((df["hour_sin"].abs() <= 1).all())
        self.assertTrue((df["doy_cos"].abs() <= 1).all())
        # interaction term is zero when wind is not low, equals revision when it is
        low = df["wind_forecast_5h_mwh"] <= LOW_WIND_CUT_MWH
        self.assertTrue((df.loc[~low, "wind_revision_when_low_wind_mwh"] == 0).all())
        self.assertTrue(
            np.allclose(
                df.loc[low, "wind_revision_when_low_wind_mwh"], df.loc[low, "wind_revision_mwh"]
            )
        )

    def test_no_outcome_field_in_features(self) -> None:
        from src.p10_model import FEATURES

        self.assertNotIn("balancing_spread_eur_mwh", FEATURES)
        self.assertNotIn("residual_load_actual_mwh", FEATURES)
        self.assertNotIn("target_label", FEATURES)


class SplitTests(unittest.TestCase):
    def test_splits_are_time_ordered_and_disjoint(self) -> None:
        df = build_features(_base(60))
        config = {"periods": {"boundary_timezone": "Europe/Copenhagen", "holdout": {"start_date": "2024-07-01"}}}
        m = _split_masks(df, config)
        self.assertEqual(int((m["train"] & m["calibration"]).sum()), 0)
        self.assertEqual(int((m["calibration"] & m["validation"]).sum()), 0)
        tz = "Europe/Copenhagen"
        t_end = pd.Timestamp(TRAIN_END_LOCAL, tz=tz).tz_convert("UTC")
        c_end = pd.Timestamp(CALIBRATION_END_LOCAL, tz=tz).tz_convert("UTC")
        self.assertTrue((df.loc[m["train"], "delivery_start_utc"] < t_end).all())
        self.assertTrue((df.loc[m["calibration"], "delivery_start_utc"] >= t_end).all())
        self.assertTrue((df.loc[m["validation"], "delivery_start_utc"] >= c_end).all())


class BrierTests(unittest.TestCase):
    def test_multiclass_brier_sum_convention(self) -> None:
        classes = ["UP", "DOWN", "NEUTRAL"]
        y = np.array(["DOWN", "DOWN"])
        perfect = np.array([[0, 1, 0], [0, 1, 0]], dtype=float)
        worst = np.array([[1, 0, 0], [1, 0, 0]], dtype=float)
        self.assertAlmostEqual(_multiclass_brier(y, perfect, classes), 0.0)
        self.assertAlmostEqual(_multiclass_brier(y, worst, classes), 2.0)


if __name__ == "__main__":
    unittest.main()
