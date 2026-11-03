"""A14.14: offline consistency tests using the real journal comparator.

No production API, real trading, native handles, or external dependencies.
"""
import json
import unittest
from unittest.mock import patch

import f3_int121_a14_11_budget as budget


class Clock:
    def __init__(self):
        self.now = 1_000_000_000

    def __call__(self):
        return self.now

    def advance(self, amount):
        self.now += amount


class PathEvents:
    def __init__(self, clock, events):
        self.clock = clock
        self.events = list(events)
        self.calls = 0

    def read_bytes(self):
        self.calls += 1
        if not self.events:
            raise AssertionError('Unexpected additional read')
        event, elapsed_ns = self.events.pop(0)
        self.clock.advance(elapsed_ns)
        if isinstance(event, BaseException):
            raise event
        return event


def expected_record():
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


def encoded(record):
    return json.dumps(record, sort_keys=True, separators=(',', ':')).encode('utf-8')


class JournalConsistencyTests(unittest.TestCase):
    def test_t01_tampered_journal_is_rejected_by_real_comparator(self):
        clock = Clock()
        expected = expected_record()
        altered = dict(expected, sequence=2)
        path = PathEvents(clock, [(encoded(altered), 1)])
        result = budget.read(path, expected, timeout=0.1, clock_ns=clock)
        self.assertEqual(result['status'], 'CONTENT_MISMATCH')
        self.assertFalse(result['verification']['accepted'])
        self.assertEqual(result['verification']['reason'], 'CONTENT_MISMATCH')
        self.assertIsNone(result['error'])
        self.assertEqual(path.calls, 1)
        self.assertFalse(result['production_api_changed'])

    def test_t02_os_read_failure_is_not_reported_as_success(self):
        clock = Clock()
        expected = expected_record()
        failure = OSError(5, 'simulated I/O failure')
        path = PathEvents(clock, [(failure, 1)])
        result = budget.read(path, expected, timeout=0.1, clock_ns=clock)
        self.assertEqual(result['status'], 'JOURNAL_READ_ERROR')
        self.assertIsNone(result['raw'])
        self.assertIsNone(result['verification'])
        self.assertEqual(result['error']['type'], 'OSError')
        self.assertEqual(result['error']['errno'], 5)
        self.assertEqual(len(result['attempts']), 1)
        self.assertEqual(path.calls, 1)
        self.assertFalse(result['production_api_changed'])

    def test_t03_transient_denial_then_valid_read_recovers_with_integrity(self):
        clock = Clock()
        expected = expected_record()
        raw = encoded(expected)
        path = PathEvents(clock, [
            (PermissionError(13, 'simulated temporary denial'), 1),
            (raw, 1),
        ])
        # Deterministic, no real sleep and no Windows handles.
        with patch.object(budget.time, 'sleep', side_effect=lambda seconds: clock.advance(int(seconds * 1e9))):
            result = budget.read(path, expected, timeout=0.1, clock_ns=clock)
        self.assertEqual(result['status'], 'CONTENT_MATCH')
        self.assertTrue(result['verification']['accepted'])
        self.assertEqual(result['verification']['reason'], 'CONTENT_MATCH')
        self.assertEqual(result['raw'], raw)
        self.assertIsNone(result['error'])
        self.assertEqual(len(result['attempts']), 2)
        self.assertEqual(result['attempts'][0]['error']['type'], 'PermissionError')
        self.assertIsNone(result['attempts'][1]['error'])
        self.assertEqual(path.calls, 2)
        self.assertFalse(result['strict_deadline_guaranteed'])
        self.assertFalse(result['production_api_changed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
