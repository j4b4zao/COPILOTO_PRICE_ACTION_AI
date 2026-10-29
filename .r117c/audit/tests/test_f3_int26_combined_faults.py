"""F3-INT-26: combined-fault regression, fixtures only, no native interfaces."""
import importlib.util
from pathlib import Path
import sys
import unittest

p = Path(__file__).resolve().parent / 'test_f3_int24_multicreation_inventory.py'
spec = importlib.util.spec_from_file_location('int26_multi_base', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
m = base.m


class CombinedFaults(unittest.TestCase):
    def h(self, omit=(), known=True):
        return base.MultiAttemptInventory().setup_h(known=known, omit=omit)

    def create(self, h):
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))

    def test_late_negative_job_and_stale_ticket(self):
        h = self.h()
        self.create(h)
        ticket = h.eligible()
        self.assertIsNotNone(ticket)
        h.put(h.fact('J', 'JOB', 'NONEMPTY'))
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['J'])
        h.check()

    def test_late_cleanup_failure_and_stale_ticket(self):
        h = self.h()
        self.create(h)
        ticket = h.eligible()
        self.assertIsNotNone(ticket)
        h.put(h.fact('L', 'RESOURCES', 'FAILED'))
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['L'])
        self.assertIn('CLEANUP_FAILED', h.s.failures)
        h.check()

    def test_late_creation_conflict_with_new_generation(self):
        h = self.h()
        self.create(h)
        ticket = h.eligible()
        self.assertIsNotNone(ticket)
        h.lease = h.r.acquire(2, 'exclusive-2')
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.target, h.child)))
        self.assertTrue(h.r.evaluate()['X'])
        self.assertFalse(h.r.close(ticket))
        self.assertNotEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        h.check()

    def test_unknown_attempt_plus_negative_job_blocks(self):
        h = self.h()
        self.create(h)
        h.put(h.fact('C', 'unknown', 'CREATED', processes=(m.Process('boot', 199, 'new', 'ref-new'),)))
        h.put(h.fact('J', 'JOB', 'NONEMPTY'))
        self.assertFalse(h.r.evaluate()['C'])
        self.assertFalse(h.finish())
        h.check()

    def test_duplicate_cross_attempt_and_cleanup_failure(self):
        h = self.h()
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target, h.child)))
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
        h.put(h.fact('L', 'RESOURCES', 'FAILED'))
        self.assertFalse(h.r.evaluate()['C'])
        self.assertFalse(h.finish())
        self.assertIn('CLEANUP_FAILED', h.s.failures)
        h.check()

    def test_discovered_descendant_without_exit_and_late_nonempty(self):
        h = self.h(known=False, omit=('P', 'H'))
        self.create(h)
        for p in (h.aux, h.target):
            h.put(h.fact('P', p.key, 'EXIT', processes=(p,)))
        for p in (h.target, h.child):
            h.put(h.fact('H', p.key, 'CONTAINED', processes=(p,)))
        h.put(h.fact('J', 'JOB', 'NONEMPTY'))
        self.assertFalse(h.r.evaluate()['P'])
        self.assertFalse(h.r.evaluate()['J'])
        self.assertFalse(h.finish())
        h.check()

    def test_stale_lease_cannot_add_after_generation_change(self):
        h = self.h()
        self.create(h)
        old = h.lease
        h.lease = h.r.acquire(2, 'exclusive-2')
        e = h.mint(h.fact('J', 'JOB', 'NONEMPTY'))
        before = len(h.s.evidence)
        self.assertEqual(h.add(e, lease=old), 'STALE_LEASE')
        self.assertEqual(len(h.s.evidence), before)
        self.assertFalse(h.r.evaluate()['J'])
        h.check()

    def test_closed_session_late_conflict_contested_externally(self):
        h = self.h()
        self.create(h)
        self.assertTrue(h.finish())
        h.put(h.fact('P', h.child.key, 'ALIVE', processes=(h.child,)))
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertTrue(h.s.contestations)
        self.assertFalse(h.s.conclusion_trusted)
        h.check()

if __name__ == '__main__':
    unittest.main()
