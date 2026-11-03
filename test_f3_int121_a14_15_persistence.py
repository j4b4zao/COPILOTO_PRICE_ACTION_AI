"""A14.15: offline persistence and recovery adversarial regression.

A fresh reader instance models a new read, not a process restart or crash
 durability guarantee. No production API, real trading, or native handles.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import f3_int121_a14_11_budget as budget


def record():
    return {
        'schema': 'A14_7_STARTUP_RECORD',
        'subject_cleanup_scope': 'INNER_JOB_AND_DIRECT_LAUNCH_PROCESS_ONLY',
        'f3': 'OPEN',
        'offline': True,
        'simulation_only': True,
        'real_operations_authorized': False,
        'runtime_modified': False,
        'production_api_changed': False,
        'constructor_evidence_is_private': True,
        'full_subtree_exit_requires_outer_safety_proof': True,
        'sequence': 1,
    }


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


class FailingPath:
    def __init__(self, failure):
        self.failure = failure
        self.calls = 0

    def read_bytes(self):
        self.calls += 1
        raise self.failure


class PersistenceTests(unittest.TestCase):
    def test_t01_fresh_reader_accepts_unchanged_persisted_record(self):
        expected = record()
        original = encode(expected)
        with TemporaryDirectory(prefix='a14_15_') as directory:
            path = Path(directory) / 'journal.json'
            path.write_bytes(original)
            first = budget.read(path, expected)
            second = budget.read(Path(str(path)), expected)
            for result in (first, second):
                self.assertEqual(result['status'], 'CONTENT_MATCH')
                self.assertTrue(result['verification']['accepted'])
                self.assertEqual(result['verification']['sha256'],
                                 hashlib.sha256(original).hexdigest())
                self.assertFalse(result['production_api_changed'])
                self.assertFalse(result['strict_deadline_guaranteed'])

    def test_t02_truncated_persisted_record_is_rejected(self):
        expected = record()
        with TemporaryDirectory(prefix='a14_15_') as directory:
            path = Path(directory) / 'journal.json'
            path.write_bytes(encode(expected)[:-1])
            result = budget.read(path, expected)
            self.assertEqual(result['status'], 'INVALID_JSON')
            self.assertFalse(result['verification']['accepted'])
            self.assertIsNone(result['error'])
            self.assertFalse(result['production_api_changed'])

    def test_t03_replaced_persisted_record_is_rejected(self):
        expected = record()
        with TemporaryDirectory(prefix='a14_15_') as directory:
            path = Path(directory) / 'journal.json'
            path.write_bytes(encode(expected))
            baseline = budget.read(path, expected)
            self.assertEqual(baseline['status'], 'CONTENT_MATCH')
            changed = dict(expected, sequence=2)
            path.write_bytes(encode(changed))
            result = budget.read(Path(str(path)), expected)
            self.assertEqual(result['status'], 'CONTENT_MISMATCH')
            self.assertFalse(result['verification']['accepted'])
            self.assertNotEqual(result['verification']['sha256'],
                                baseline['verification']['sha256'])
            self.assertFalse(result['production_api_changed'])

    def test_t04_recovery_read_error_never_reports_success(self):
        path = FailingPath(OSError(5, 'simulated recovery I/O failure'))
        result = budget.read(path, record())
        self.assertEqual(path.calls, 1)
        self.assertEqual(result['status'], 'JOURNAL_READ_ERROR')
        self.assertIsNone(result['raw'])
        self.assertIsNone(result['verification'])
        self.assertEqual(result['error']['errno'], 5)
        self.assertEqual(result['attempts'][0]['error']['errno'], 5)
        self.assertFalse(result['production_api_changed'])
        self.assertFalse(result['strict_deadline_guaranteed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
