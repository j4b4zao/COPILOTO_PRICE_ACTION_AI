"""Certification scope and legacy compatibility for the offline journal."""
from pathlib import Path
import tempfile
import unittest

import f3_int121_a14_11_budget as budget
from test_f3_int121_a14_15_persistence import encode, record


class CertificationTests(unittest.TestCase):
    def check_read(self, expected, status, accepted):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            path.write_bytes(encode(expected))
            result = budget.read(path, expected)
        self.assertEqual(result["status"], status)
        self.assertIs(result["verification"]["accepted"], accepted)
        self.assertFalse(result["production_api_changed"])

    def test_legacy_record_without_certification_is_accepted(self):
        self.check_read(record(), "CONTENT_MATCH", True)

    def test_explicit_false_certification_is_accepted(self):
        self.check_read(dict(record(), certification=False), "CONTENT_MATCH", True)

    def test_forbidden_or_mistyped_certification_is_rejected(self):
        for value in (True, 0, 1, "false", None, []):
            with self.subTest(value=value):
                self.check_read(dict(record(), certification=value), "INVALID_SCOPE", False)
