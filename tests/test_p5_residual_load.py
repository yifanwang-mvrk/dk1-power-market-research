from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.p5_residual_load import (
    CONSUMPTION,
    SOLAR_ACTUAL,
    WIND_ACTUAL,
    build_rl_actual,
    build_rl_known,
    signed_quantile_buckets,
    spearman_ci,
)


class ResidualLoadActualTests(unittest.TestCase):
    def test_residual_load_is_consumption_minus_wind_and_solar(self) -> None:
        row = {c: 0.0 for c in [CONSUMPTION, *WIND_ACTUAL, *SOLAR_ACTUAL]}
        row[CONSUMPTION] = 3000.0
        row[WIND_ACTUAL[0]] = 800.0
        row[WIND_ACTUAL[1]] = 400.0
        row[SOLAR_ACTUAL[0]] = 200.0
        frame = pd.DataFrame([row, {**row, CONSUMPTION: None}])
        out = build_rl_actual(frame)
        self.assertAlmostEqual(out.loc[0, "residual_load_actual_mwh"], 3000 - 1200 - 200)
        self.assertTrue(out.loc[0, "rl_actual_available"])
        self.assertTrue(pd.isna(out.loc[1, "residual_load_actual_mwh"]))


class ClimatologyProxyTests(unittest.TestCase):
    def test_climatology_is_lagged_and_pit_safe(self) -> None:
        n = 40
        frame = pd.DataFrame(
            {
                "delivery_start_utc": pd.date_range("2022-01-03", periods=n, freq="7D", tz="UTC"),
                "local_weekday": ["Monday"] * n,
                "local_hour": [8] * n,
                CONSUMPTION: np.arange(n, dtype=float) + 100.0,
                "forecast_5_hour_offshore_wind_mwh_per_hour": [10.0] * n,
                "forecast_5_hour_onshore_wind_mwh_per_hour": [20.0] * n,
                "forecast_5_hour_solar_mwh_per_hour": [5.0] * n,
            }
        )
        out = build_rl_known(frame)
        # first 3 occurrences have no lagged window
        self.assertTrue(out["consumption_climatology_mwh"].iloc[:3].isna().all())
        # occurrence 4 (index 3) uses the mean of occurrences 0..0 -> shift(3) of expanding mean
        self.assertAlmostEqual(out["consumption_climatology_mwh"].iloc[3], 100.0)
        # occurrence 5 (index 4) uses mean of occurrences 0..1 = 100.5
        self.assertAlmostEqual(out["consumption_climatology_mwh"].iloc[4], 100.5)
        self.assertAlmostEqual(
            out["residual_load_known_mwh"].iloc[4], 100.5 - 35.0
        )


class HelperTests(unittest.TestCase):
    def test_signed_quantile_buckets_five_groups(self) -> None:
        values = pd.Series(np.arange(-500, 500, dtype=float))
        bucket, edges = signed_quantile_buckets(values, (0.2, 0.4, 0.6, 0.8))
        self.assertEqual(len(edges), 4)
        self.assertEqual(sorted(bucket.dropna().unique().tolist()), [1, 2, 3, 4, 5])

    def test_spearman_ci_sign_check(self) -> None:
        x = pd.Series(np.arange(500, dtype=float))
        y = pd.Series(np.arange(500, dtype=float) + np.random.default_rng(1).normal(0, 5, 500))
        out = spearman_ci(x, y, predicted_sign=1)
        self.assertTrue(out["association_supported"])
        out_wrong = spearman_ci(x, y, predicted_sign=-1)
        self.assertFalse(out_wrong["association_supported"])


if __name__ == "__main__":
    unittest.main()
