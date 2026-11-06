"""Regression coverage for the opt-in journal byte limit."""

import hashlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import f3_int121_a14_11_budget as budget
from test_f3_int121_a14_15_persistence import encode, record


class JournalByteLimitTests(unittest.TestCase):
    def test_equal_to_limit_matches_with_complete_evidence(self):
        expected = record()
        raw = encode(expected)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            path.write_bytes(raw)
            result = budget.read(path, expected, max_bytes=len(raw))

        self.assertEqual(result["status"], "CONTENT_MATCH")
        self.assertEqual(result["raw"], raw)
        self.assertEqual(result["verification"]["size"], len(raw))
        self.assertEqual(result["verification"]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_oversized_read_does_not_pass_prefix_to_comparator(self):
        expected = record()
        raw = encode(expected)
        limit = len(raw) - 1
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            path.write_bytes(raw + b" " * 100)
            with patch.object(budget.journal, "compare") as compare:
                result = budget.read(path, expected, max_bytes=limit)

        compare.assert_not_called()
        self.assertEqual(result["status"], "JOURNAL_TOO_LARGE")
        self.assertIsNone(result["raw"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["verification"], {
            "accepted": False,
            "reason": "JOURNAL_TOO_LARGE",
            "sha256": None,
            "size": None,
            "bytes_read": limit + 1,
            "limit": limit,
        })

    def test_retry_after_denial_applies_limit(self):
        expected = record()
        raw = encode(expected)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            path.write_bytes(raw)
            with patch.object(Path, "open", side_effect=[
                PermissionError(13, "synthetic denial"), path.open("rb")
            ]), patch.object(budget.time, "sleep"):
                result = budget.read(
                    path, expected, max_bytes=len(raw) - 1,
                    clock_ns=iter(range(10)).__next__,
                )

        self.assertEqual(result["status"], "JOURNAL_TOO_LARGE")
        first, second = result["attempts"]
        self.assertEqual(first["error"]["type"], "PermissionError")
        self.assertIsNone(second["error"])

    def test_invalid_limits_are_rejected_before_io(self):
        for limit in (0, -1, True, 1.0, "64", sys.maxsize):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                budget.read(None, record(), max_bytes=limit)
