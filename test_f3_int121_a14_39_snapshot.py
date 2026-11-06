"""The journal verifies the bytes captured by each individual read."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from f3_int121_a14_11_budget import read
from test_f3_int121_a14_15_persistence import encode, record


class ReplacingReader:
    def __init__(self, journal, replacement):
        self.journal = journal
        self.replacement = replacement

    def read_bytes(self):
        captured = self.journal.read_bytes()
        self.replacement.replace(self.journal)
        return captured


class SnapshotTests(unittest.TestCase):
    def test_replacement_after_read_is_observed_on_next_call(self):
        expected = record()
        original = encode(expected)
        updated = encode(dict(expected, sequence=expected["sequence"] + 1))

        with TemporaryDirectory() as directory:
            journal = Path(directory) / "journal.json"
            replacement = Path(directory) / "replacement.json"
            journal.write_bytes(original)
            replacement.write_bytes(updated)

            first = read(ReplacingReader(journal, replacement), expected)
            second = read(journal, expected)

        for result, raw, status in (
            (first, original, "CONTENT_MATCH"),
            (second, updated, "CONTENT_MISMATCH"),
        ):
            with self.subTest(status=status):
                self.assertEqual(result["status"], status)
                self.assertEqual(result["raw"], raw)
                self.assertEqual(result["verification"]["size"], len(raw))
                self.assertEqual(
                    result["verification"]["sha256"], hashlib.sha256(raw).hexdigest()
                )

    def test_partial_write_is_rejected_until_completed(self):
        expected = record()
        original = encode(expected)
        midpoint = len(original) // 2

        with TemporaryDirectory() as directory:
            journal = Path(directory) / "journal.json"
            with journal.open("wb") as writer:
                writer.write(original[:midpoint])
                writer.flush()
                partial = read(journal, expected)
                writer.write(original[midpoint:])

            complete = read(journal, expected)

        self.assertEqual(partial["status"], "INVALID_JSON")
        self.assertFalse(partial["verification"]["accepted"])
        self.assertEqual(partial["verification"]["size"], midpoint)
        self.assertEqual(
            partial["verification"]["sha256"],
            hashlib.sha256(original[:midpoint]).hexdigest(),
        )
        self.assertEqual(complete["status"], "CONTENT_MATCH")
        self.assertEqual(complete["raw"], original)
