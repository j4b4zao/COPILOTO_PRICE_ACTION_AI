"""F3-INT-25: adversarial synthetic inventory coverage; no native effects."""
import importlib.util
from pathlib import Path
import sys
import unittest

p = Path(__file__).resolve().parent / 'test_f3_int24_multicreation_inventory.py'
spec = importlib.util.spec_from_file_location('int25_inventory_base', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
m = base.m


class InventoryAdversarial(unittest.TestCase):
    def h(self, known=True, omit=()):
        return base.MultiAttemptInventory().setup_h(known=known, omit=omit)

    def complete(self, h):
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))

    def test_partition_reversed_order(self):
        h = self.h()
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        self.assertTrue(h.finish())
        h.check()

    def test_unknown_attempt_cannot_expand_inventory(self):
        h = self.h()
        self.complete(h)
        h.put(h.fact('C', 'c', 'CREATED', processes=(m.Process('boot',103,'birth-extra','ref-extra'),)))
        self.assertFalse(h.r.evaluate()['C'])
        self.assertFalse(h.finish())
        h.check()

    def test_failed_attempt_with_process_is_not_complete(self):
        h = self.h()
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        h.put(h.fact('C', 'b', 'FAILED', processes=(h.child,)))
        self.assertFalse(h.r.evaluate()['C'])
        h.check()

    def test_created_attempt_without_process_is_not_complete(self):
        h = self.h()
        h.put(h.fact('C', 'a', 'CREATED', processes=()))
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.target,h.child)))
        self.assertFalse(h.r.evaluate()['C'])
        h.check()

    def test_conflicting_late_inventory_invalidates_ticket(self):
        h = self.h()
        self.complete(h)
        ticket = h.eligible()
        self.assertIsNotNone(ticket)
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.target,h.child)))
        self.assertTrue(h.r.evaluate()['X'])
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['J'])
        h.check()

    def test_duplicate_identical_evidence_is_idempotent(self):
        h = self.h()
        self.complete(h)
        e = next(e for e in h.s.evidence if e.fact.obligation == 'C' and e.fact.subject == 'a')
        rev = h.s.revision
        self.assertEqual(h.add(e), 'DUPLICATE_NO_EFFECT')
        self.assertEqual(h.s.revision, rev)
        self.assertTrue(h.finish())
        h.check()

    def test_extra_descendant_requires_exit_and_containment(self):
        h = self.h(known=False, omit=('P','H'))
        self.complete(h)
        self.assertFalse(h.r.evaluate()['P'])
        self.assertFalse(h.r.evaluate()['H'])
        for p in (h.aux,h.target,h.child):
            h.put(h.fact('P', p.key, 'EXIT', processes=(p,)))
        for p in (h.target,h.child):
            h.put(h.fact('H', p.key, 'CONTAINED', processes=(p,)))
        self.assertTrue(h.finish())
        h.check()

    def test_new_generation_invalidates_old_closure_ticket(self):
        h = self.h()
        self.complete(h)
        ticket = h.eligible()
        self.assertIsNotNone(ticket)
        h.lease = h.r.acquire(2, 'exclusive-2')
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['J'])
        h.check()

if __name__ == '__main__':
    unittest.main()
