from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.p10_unlock_gate import verify_prior_non_use


class UnlockGateTests(unittest.TestCase):
    def test_p10_2_record_attested_prior_non_use(self) -> None:
        # The P10.2 unlock record is a committed historical artifact: at the time
        # it was written the holdout had never been requested, fetched or read.
        record = json.loads(
            Path("research/evidence/p10_holdout_unlock/unlock_record_2026-09-06.json").read_text()
        )
        v = record["prior_non_use_verification"]
        self.assertTrue(v["prior_non_use_verified"])
        self.assertTrue(all(f["within_development"] for f in v["raw_files"]))
        self.assertTrue(all(f["before_holdout"] for f in v["processed_files"]))
        self.assertEqual(record["owner_approval"]["required_for"], "P10.3 (unlock + holdout fetch + evaluation)")

    def test_development_raw_and_processed_data_stays_within_development(self) -> None:
        # Independent of holdout state, the development inputs must never contain
        # a holdout row.
        result = verify_prior_non_use(Path.cwd())
        for f in result["raw_files"]:
            self.assertLess(f["max_hour_utc"], "2024-07-01", f["file"])
            self.assertEqual(len(f["sha256"]), 64)
        self.assertTrue(all(f["before_holdout"] for f in result["processed_files"]))


if __name__ == "__main__":
    unittest.main()
