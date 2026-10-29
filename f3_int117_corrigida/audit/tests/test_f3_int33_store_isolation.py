"""F3-INT-33: simulated ledger copy/isolation boundary tests; no real persistence."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

p = Path(__file__).with_name('test_f3_int32_worker_restart_shared_store.py')
spec = importlib.util.spec_from_file_location('int33_base', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
m = base.m

class StoreIsolation(unittest.TestCase):
    def test_snapshot_is_not_a_shared_authority(self):
        h, ticket = base.ready()
        snapshot = copy.deepcopy(h.s)
        self.assertIsNot(snapshot, h.s)
        self.assertIsNot(snapshot._commit_gate, h.s._commit_gate)
        self.assertEqual(snapshot.evidence_digest, h.s.evidence_digest)
        self.assertEqual(snapshot.f3, 'OPEN')
        self.assertFalse(any(getattr(snapshot, flag) for flag in m.FLAGS))
        self.assertIsNotNone(ticket)

    def test_independent_generation_mutation_does_not_replicate(self):
        h, ticket = base.ready()
        snapshot = copy.deepcopy(h.s)
        replica = m.Recovery(snapshot, h.v)
        original_generation = h.s.generation
        replica.acquire(snapshot.generation + 1, 'replica-owner')
        self.assertEqual(h.s.generation, original_generation)
        self.assertNotEqual(snapshot.generation, h.s.generation)
        self.assertFalse(replica.close(ticket))
        h.check()

    def test_original_commit_does_not_propagate_to_snapshot(self):
        h, ticket = base.ready()
        snapshot = copy.deepcopy(h.s)
        self.assertTrue(h.r.close(ticket))
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertNotEqual(snapshot.phase, m.Phase.CLOSED_RECOVERED)
        self.assertIsNone(snapshot.closure)
        self.assertEqual(snapshot.f3, 'OPEN')
        self.assertFalse(any(getattr(snapshot, flag) for flag in m.FLAGS))
        h.check()

    def test_shared_instance_serializes_duplicate_commit(self):
        h, ticket = base.ready()
        other = m.Recovery(h.s, h.v)
        self.assertTrue(other.close(ticket))
        self.assertFalse(h.r.close(ticket))
        self.assertEqual(h.s.closure, ticket)
        h.check()

if __name__ == '__main__':
    unittest.main()
