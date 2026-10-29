"""F3-INT-27: deterministic bounded combinatorial checks; simulation only."""
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest

p = Path(__file__).resolve().parent / 'test_f3_int26_combined_faults.py'
spec = importlib.util.spec_from_file_location('int27_base', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
m = base.m

class CombinatorialInvariants(unittest.TestCase):
    def h(self):
        return base.CombinedFaults().h()

    def invariant(self, h):
        h.check()
        self.assertTrue(h.s.original.revoked)
        self.assertTrue(h.s.original.admission_closed)
        self.assertFalse(h.s.aggregate_success)
        self.assertFalse(any(getattr(h.s, flag, False) for flag in m.FLAGS))

    def test_all_orderings_of_two_attempts_and_negative_job(self):
        # 3! = 6 event orders; no premature closure after a negative J.
        actions = ('a', 'b', 'negative_j')
        for order in itertools.permutations(actions):
            with self.subTest(order=order):
                h = self.h()
                for action in order:
                    if action == 'a':
                        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
                    elif action == 'b':
                        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
                    else:
                        h.put(h.fact('J', 'JOB', 'NONEMPTY'))
                    self.invariant(h)
                self.assertFalse(h.r.evaluate()['J'])
                # A fresh qualified J/L observation may legitimately supersede the old negative J.
                self.assertTrue(h.finish())
                self.invariant(h)

    def test_cross_attempt_duplicates_and_unknown_attempt_orderings(self):
        # 3! = 6 sequences; inconsistent ownership or unknown attempt never qualifies.
        for order in itertools.permutations(('a', 'b_duplicate', 'unknown')):
            with self.subTest(order=order):
                h = self.h()
                for action in order:
                    if action == 'a':
                        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target, h.child)))
                    elif action == 'b_duplicate':
                        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
                    else:
                        h.put(h.fact('C', 'foreign', 'CREATED', processes=(m.Process('boot', 199, 'foreign', 'ref'),)))
                    self.invariant(h)
                self.assertFalse(h.r.evaluate()['C'])
                self.assertFalse(h.finish())

    def test_ticket_invalidated_by_material_faults_and_generation(self):
        # Four fault types independently invalidate a previously eligible ticket.
        for fault in ('job', 'cleanup', 'generation', 'creation_conflict'):
            with self.subTest(fault=fault):
                h = self.h()
                h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
                h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
                ticket = h.eligible()
                self.assertIsNotNone(ticket)
                if fault == 'job':
                    h.put(h.fact('J', 'JOB', 'NONEMPTY'))
                elif fault == 'cleanup':
                    h.put(h.fact('L', 'RESOURCES', 'FAILED'))
                elif fault == 'generation':
                    h.lease = h.r.acquire(2, 'exclusive-2')
                else:
                    h.put(h.fact('C', 'b', 'CREATED', processes=(h.target, h.child)))
                self.assertFalse(h.r.close(ticket))
                self.invariant(h)

    def test_terminal_contestation_preserves_revocation(self):
        h = self.h()
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
        self.assertTrue(h.finish())
        self.invariant(h)
        h.put(h.fact('P', h.child.key, 'ALIVE', processes=(h.child,)))
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertFalse(h.s.conclusion_trusted)
        self.invariant(h)

if __name__ == '__main__':
    unittest.main()
