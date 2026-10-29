"""F3-INT-29: bounded longer interleavings and synthetic reduction; no native interfaces."""
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest

path = Path(__file__).with_name('test_f3_int28_sequence_minimizer.py')
spec = importlib.util.spec_from_file_location('int29_previous', path)
prev = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prev
spec.loader.exec_module(prev)
m = prev.m

class LongSequences(unittest.TestCase):
    def test_six_action_interleavings_with_late_negative(self):
        # 6! = 720 orderings, bounded deterministic exhaustive permutations of this fixture.
        actions = ('CREATE_A', 'CREATE_B', 'NEGATIVE_JOB', 'NEGATIVE_CLEANUP', 'NEW_GENERATION', 'LATE_CONFLICT')
        count = 0
        for order in itertools.permutations(actions):
            h, accepted = prev.replay(order + ('QUALIFY', 'CLOSE'))
            self.assertFalse(accepted, order)
            self.assertNotEqual(h.s.phase, m.Phase.CLOSED_RECOVERED, order)
            count += 1
        self.assertEqual(count, 720)

    def test_interleaved_qualify_close_with_stale_ticket(self):
        faults = ('NEGATIVE_JOB', 'NEGATIVE_CLEANUP', 'NEW_GENERATION', 'LATE_CONFLICT')
        count = 0
        for first, second in itertools.permutations(faults, 2):
            for prefix in (('CREATE_A', 'CREATE_B'), ('CREATE_B', 'CREATE_A')):
                h, accepted = prev.replay(prefix + ('QUALIFY', first, second, 'CLOSE'))
                self.assertFalse(accepted)
                self.assertNotEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
                count += 1
        self.assertEqual(count, 24)

    def test_complex_synthetic_minimization_is_one_minimal(self):
        # Two alternative triggers; no claim of globally shortest counterexample.
        def oracle(seq):
            return (('NEGATIVE_JOB' in seq and 'CLOSE' in seq and seq.index('NEGATIVE_JOB') < seq.index('CLOSE'))
                    or ('LATE_CONFLICT' in seq and 'NEW_GENERATION' in seq and
                        seq.index('LATE_CONFLICT') < seq.index('NEW_GENERATION')))
        trace = ('CREATE_A', 'NEGATIVE_JOB', 'CREATE_B', 'LATE_CONFLICT',
                 'NEGATIVE_CLEANUP', 'NEW_GENERATION', 'CLOSE', 'CREATE_A')
        result = prev.minimize(trace, oracle)
        self.assertTrue(oracle(result))
        self.assertLess(len(result), len(trace))
        for index in range(len(result)):
            self.assertFalse(oracle(result[:index] + result[index + 1:]))
        self.assertEqual(prev.minimize(trace, oracle), result)

    def test_nonreproducing_trace_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'INPUT_DOES_NOT_REPRODUCE'):
            prev.minimize(('CREATE_A', 'CREATE_B', 'CLOSE'),
                          lambda seq: 'LATE_CONFLICT' in seq and 'NEW_GENERATION' in seq)

if __name__ == '__main__':
    unittest.main()
