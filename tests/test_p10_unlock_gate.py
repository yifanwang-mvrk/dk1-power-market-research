from __future__ import annotations

import unittest
from pathlib import Path

from src.p10_unlock_gate import verify_prior_non_use


class UnlockGateTests(unittest.TestCase):
    def test_prior_non_use_is_verified_on_the_current_repo(self) -> None:
        result = verify_prior_non_use(Path.cwd())
        self.assertTrue(result["config_holdout_state"]["locked_and_fetch_disabled"])
        self.assertTrue(all(f["within_development"] for f in result["raw_files"]))
        self.assertTrue(all(f["before_holdout"] for f in result["processed_files"]))
        self.assertTrue(result["prior_non_use_verified"])

    def test_every_raw_file_stops_before_the_holdout(self) -> None:
        result = verify_prior_non_use(Path.cwd())
        for f in result["raw_files"]:
            self.assertLess(f["max_hour_utc"], "2024-07-01", f["file"])
            self.assertEqual(len(f["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
