"""A14.13: offline adversarial tests for the private retry-budget reader.

No production API, real trading, Windows handles, or external dependencies.
"""
import unittest
from unittest.mock import patch

import f3_int121_a14_11_budget as reader


class FakeClock:
    def __init__(self, initial=1_000_000_000):
        self.now = initial

    def __call__(self):
        return self.now

    def advance(self, nanoseconds):
        self.now += nanoseconds


class FakePath:
    def __init__(self, clock, events):
        self.clock = clock
        self.events = list(events)
        self.calls = 0

    def read_bytes(self):
        self.calls += 1
        if not self.events:
            raise AssertionError('Unexpected additional read')
        action, elapsed_ns = self.events.pop(0)
        self.clock.advance(elapsed_ns)
        if isinstance(action, BaseException):
            raise action
        return action


def denied():
    return PermissionError(13, 'simulated access denied')


class AdversarialBudgetTests(unittest.TestCase):
    def test_callback_exception_is_observable_not_false_success(self):
        clock = FakeClock()
        path = FakePath(clock, [(denied(), 1)])
        def callback(_error):
            raise RuntimeError('A14_13_CALLBACK_FAILURE')
        with self.assertRaisesRegex(RuntimeError, 'A14_13_CALLBACK_FAILURE'):
            reader.read(path, {}, timeout=0.1, after_denial=callback, clock_ns=clock)
        self.assertEqual(path.calls, 1)

    def test_deadline_expires_inside_callback_without_new_read(self):
        clock = FakeClock()
        path = FakePath(clock, [(denied(), 1)])
        def callback(_error):
            clock.advance(100_000_000)
        result = reader.read(path, {}, timeout=0.1,
                             after_denial=callback, clock_ns=clock)
        self.assertEqual(result['status'], 'JOURNAL_READ_DENIED')
        self.assertEqual(path.calls, 1)
        self.assertEqual(len(result['attempts']), 1)
        self.assertEqual(result['error']['type'], 'PermissionError')
        self.assertFalse(result['strict_deadline_guaranteed'])
        self.assertFalse(result['production_api_changed'])

    def test_read_started_before_deadline_may_finish_after(self):
        clock = FakeClock()
        payload = b'controlled-test-bytes'
        path = FakePath(clock, [(payload, 200_000_000)])
        expected_verification = {'accepted': False, 'reason': 'CONTENT_MISMATCH'}
        with patch.object(reader.journal, 'compare', return_value=expected_verification) as compare:
            result = reader.read(path, {}, timeout=0.1, clock_ns=clock)
        compare.assert_called_once_with(payload, {})
        self.assertEqual(result['status'], 'CONTENT_MISMATCH')
        self.assertGreater(result['finished_ns'], result['deadline_ns'])
        self.assertLess(result['attempts'][0]['started_ns'], result['deadline_ns'])
        self.assertFalse(result['strict_deadline_guaranteed'])
        self.assertFalse(result['production_api_changed'])
        self.assertEqual(path.calls, 1)

    def test_no_first_attempt_at_deadline(self):
        clock = FakeClock()
        path = FakePath(clock, [])
        # First clock() starts budget, second clock() reaches deadline.
        original = clock.__call__
        reads = [0]
        def ticking_clock():
            reads[0] += 1
            if reads[0] == 2:
                clock.advance(100_000_000)
            return original()
        result = reader.read(path, {}, timeout=0.1, clock_ns=ticking_clock)
        self.assertEqual(result['status'], 'JOURNAL_READ_BUDGET_EXHAUSTED')
        self.assertEqual(result['attempts'], [])
        self.assertEqual(path.calls, 0)

    def test_last_denial_preserved_when_callback_consumes_budget(self):
        clock = FakeClock()
        path = FakePath(clock, [(denied(), 1)])
        def callback(_error):
            clock.advance(110_000_000)
        result = reader.read(path, {}, timeout=0.1,
                             after_denial=callback, clock_ns=clock)
        self.assertEqual(result['status'], 'JOURNAL_READ_DENIED')
        self.assertEqual(result['error'], result['attempts'][-1]['error'])
        self.assertIsNone(result['verification'])
        self.assertIsNone(result['raw'])
        self.assertEqual(path.calls, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
