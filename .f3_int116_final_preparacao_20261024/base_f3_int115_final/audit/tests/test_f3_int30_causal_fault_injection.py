"""F3-INT-30: causal-order checks and synthetic controlled fault injection, offline only."""
import importlib.util
from pathlib import Path
import sys
import unittest

p = Path(__file__).with_name('test_f3_int28_sequence_minimizer.py')
spec = importlib.util.spec_from_file_location('int30_base', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


def injected_oracle(trace):
    """Synthetic faulty closer: accepts a stale ticket after mutation; NOT production model."""
    ticket = False
    invalidated = False
    for action in trace:
        if action == 'QUALIFY':
            ticket = True
            invalidated = False
        elif action in ('NEW_GENERATION', 'LATE_CONFLICT', 'NEGATIVE_JOB', 'NEGATIVE_CLEANUP') and ticket:
            invalidated = True
        elif action == 'CLOSE' and ticket and invalidated:
            return True
    return False


class CausalFaultInjection(unittest.TestCase):
    def test_injected_stale_ticket_reduces_to_causal_triple(self):
        trace = ('CREATE_A', 'CREATE_B', 'QUALIFY', 'CREATE_A', 'NEW_GENERATION',
                 'NEGATIVE_CLEANUP', 'CLOSE', 'CREATE_B')
        reduced = base.minimize(trace, injected_oracle)
        self.assertEqual(len(reduced), 3)
        self.assertEqual(reduced[0], 'QUALIFY')
        self.assertEqual(reduced[-1], 'CLOSE')
        self.assertIn(reduced[1], ('NEW_GENERATION', 'NEGATIVE_CLEANUP'))
        for i in range(len(reduced)):
            self.assertFalse(injected_oracle(reduced[:i] + reduced[i + 1:]))

    def test_causal_reordering_disables_injected_fault(self):
        self.assertTrue(injected_oracle(('QUALIFY', 'NEW_GENERATION', 'CLOSE')))
        for trace in (('NEW_GENERATION', 'QUALIFY', 'CLOSE'),
                      ('QUALIFY', 'CLOSE', 'NEW_GENERATION'),
                      ('QUALIFY', 'NEW_GENERATION', 'QUALIFY', 'CLOSE')):
            self.assertFalse(injected_oracle(trace), trace)

    def test_real_simulated_model_rejects_injected_causal_triples(self):
        for fault in ('NEW_GENERATION', 'LATE_CONFLICT', 'NEGATIVE_JOB', 'NEGATIVE_CLEANUP'):
            with self.subTest(fault=fault):
                trace = ('CREATE_A', 'CREATE_B', 'QUALIFY', fault, 'CLOSE')
                self.assertTrue(injected_oracle(trace))
                h, accepted = base.replay(trace)
                self.assertFalse(accepted)
                self.assertNotEqual(h.s.phase, base.m.Phase.CLOSED_RECOVERED)

    def test_reducer_deterministic_and_rejects_nonreproducer(self):
        trace = ('CREATE_A', 'QUALIFY', 'LATE_CONFLICT', 'CREATE_B', 'CLOSE')
        self.assertEqual(base.minimize(trace, injected_oracle),
                         base.minimize(trace, injected_oracle))
        with self.assertRaisesRegex(ValueError, 'INPUT_DOES_NOT_REPRODUCE'):
            base.minimize(('NEW_GENERATION', 'QUALIFY', 'CLOSE'), injected_oracle)

if __name__ == '__main__':
    unittest.main()
