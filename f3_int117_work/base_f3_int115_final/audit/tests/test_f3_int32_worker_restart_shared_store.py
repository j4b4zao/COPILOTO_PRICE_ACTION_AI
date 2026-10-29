"""F3-INT-32: deterministic worker-restart / shared-store scheduling, SIMULATED ONLY.

No actual threads, persistence, distributed consensus, or native process control.
"""
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest

p = Path(__file__).with_name('test_f3_int28_sequence_minimizer.py')
spec = importlib.util.spec_from_file_location('int32_base', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
m = base.m


def ready():
    h = base.base.CombinedFaults().h()
    h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
    h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
    ticket = h.eligible()
    assert ticket is not None
    return h, ticket


class WorkerRestartSharedStore(unittest.TestCase):
    def test_restart_shares_ledger_and_rejects_duplicate_closure(self):
        h, ticket = ready()
        restarted = m.Recovery(h.s, h.v)
        self.assertIs(restarted.s, h.r.s)
        self.assertTrue(restarted.close(ticket))
        self.assertFalse(h.r.close(ticket))
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertEqual(h.s.closure, ticket)
        h.check()

    def test_all_two_worker_close_schedules_single_winner(self):
        for schedule in itertools.product((0, 1), repeat=4):
            with self.subTest(schedule=schedule):
                h, ticket = ready()
                workers = (h.r, m.Recovery(h.s, h.v))
                outcomes = [workers[i].close(ticket) for i in schedule]
                self.assertEqual(sum(outcomes), 1)
                self.assertTrue(outcomes[0])
                self.assertEqual(h.s.closure, ticket)
                h.check()

    def test_generation_rotated_by_other_worker_fences_old_ticket(self):
        for order in ((0, 1), (1, 0)):
            with self.subTest(order=order):
                h, ticket = ready()
                workers = (h.r, m.Recovery(h.s, h.v))
                workers[order[0]].acquire(h.s.generation + 1, 'restarted-worker')
                self.assertFalse(workers[order[1]].close(ticket))
                self.assertFalse(workers[order[0]].close(ticket))
                self.assertIsNone(h.s.closure)
                h.check()

    def test_mutation_from_restarted_worker_invalidates_both_tickets(self):
        for fault in ('JOB', 'CLEANUP', 'CONFLICT'):
            with self.subTest(fault=fault):
                h, ticket = ready()
                worker = m.Recovery(h.s, h.v)
                if fault == 'JOB':
                    h.put(h.fact('J', 'JOB', 'NONEMPTY'))
                elif fault == 'CLEANUP':
                    h.put(h.fact('L', 'RESOURCES', 'FAILED'))
                else:
                    h.put(h.fact('C', 'b', 'CREATED', processes=(h.target, h.child)))
                self.assertFalse(worker.close(ticket))
                self.assertFalse(h.r.close(ticket))
                self.assertIsNone(h.s.closure)
                h.check()

    def test_distinct_stores_are_not_shared_authority(self):
        h, ticket = ready()
        # Explicit limitation: copying a ledger does not model a single authority.
        import copy
        clone = copy.deepcopy(h.s)
        self.assertIsNot(clone, h.s)
        self.assertIsNot(clone._commit_gate, h.s._commit_gate)
        self.assertEqual(clone.evidence_digest, h.s.evidence_digest)
        self.assertEqual(clone.f3, 'OPEN')
        self.assertFalse(any(getattr(clone, flag) for flag in m.FLAGS))
        self.assertIsNotNone(ticket)

if __name__ == '__main__':
    unittest.main()
