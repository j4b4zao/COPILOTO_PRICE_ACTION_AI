"""Regression for oversized nesting in the private offline journal reader."""
import hashlib
from pathlib import Path
import tempfile
import unittest

import f3_int121_a14_11_budget as budget
from test_f3_int121_a14_15_persistence import encode, record


class JournalDepthTests(unittest.TestCase):
    def test_excessive_nesting_is_rejected_with_evidence(self):
        expected = record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            for opening, closing in ((b"[", b"]"), (b'{"k":', b"}")):
                with self.subTest(opening=opening):
                    raw = b'{"payload":' + opening * 10000 + b"0" + closing * 10000 + b"}"
                    path.write_bytes(raw)
                    result = budget.read(path, expected)
                    self.assertEqual(result["status"], "INVALID_JSON")
                    self.assertEqual(result["verification"], {
                        "accepted": False,
                        "reason": "INVALID_JSON",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "size": len(raw),
                    })
            path.write_bytes(encode(expected))
            self.assertEqual(budget.read(path, expected)["status"], "CONTENT_MATCH")
