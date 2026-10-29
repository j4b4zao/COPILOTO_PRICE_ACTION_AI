import unittest
from dataclasses import replace
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot
from tools.f3_int84_import_schedule_divergence import run_import_schedule
from tools.f3_int88_import_divergence_witness import ImportWitness,replay_import_witness,find_import_witness,safe_to_promote


class ImportWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial=RegistrySnapshot(); cls.a=import_requests('a','b'); cls.b=import_requests('c','d',1)
        cls.batches=(cls.a,cls.b)
        cls.left=run_import_schedule(cls.initial,cls.batches,(('prepare',0),('commit',0),('prepare',1),('commit',1)))
        cls.right=run_import_schedule(cls.initial,cls.batches,(('prepare',1),('commit',1),('prepare',0),('commit',0)))
        cls.witness=ImportWitness(cls.initial,cls.batches,cls.left,cls.right)
    def test_order_only_witness(self):
        r=replay_import_witness(self.witness); self.assertEqual(r.classification,'ORDER_ONLY')
        self.assertEqual(r.status,'IMPORT_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED')
    def test_content_witness(self):
        concurrent=run_import_schedule(self.initial,self.batches,(('prepare',0),('prepare',1),('commit',0),('commit',1)))
        self.assertEqual(replay_import_witness(replace(self.witness,right=concurrent)).classification,'CONTENT_DIVERGENCE')
    def test_version_only_witness(self):
        batches=(self.a,self.b,self.a+self.b)
        left=run_import_schedule(self.initial,batches,(('prepare',2),('commit',2),('prepare',0),('commit',0),('prepare',1),('commit',1)))
        right=run_import_schedule(self.initial,batches,(('prepare',0),('commit',0),('prepare',1),('commit',1),('prepare',2),('commit',2)))
        r=replay_import_witness(ImportWitness(self.initial,batches,left,right)); self.assertEqual(r.classification,'VERSION_ONLY')
    def test_status_tampering(self):
        bad=replace(self.left,statuses=('forged',)+self.left.statuses[1:])
        self.assertEqual(replay_import_witness(replace(self.witness,left=bad)).status,'IMPORT_WITNESS_REPLAY_MISMATCH')
    def test_snapshot_tampering(self):
        bad=replace(self.left,snapshots=self.left.snapshots[:-1]+(RegistrySnapshot(99),))
        self.assertEqual(replay_import_witness(replace(self.witness,left=bad)).status,'IMPORT_WITNESS_REPLAY_MISMATCH')
    def test_identical_trace(self):
        self.assertEqual(replay_import_witness(replace(self.witness,right=self.left)).status,'NO_IMPORT_TERMINAL_DIVERGENCE')
    def test_find_order(self):
        r=find_import_witness(self.initial,self.batches,kind='order'); self.assertEqual(r.classification,'ORDER_ONLY'); self.assertTrue(r.complete)
    def test_incomplete_prefix(self):
        r=find_import_witness(self.initial,self.batches,max_schedules=1)
        self.assertEqual(r.status,'INCOMPLETE_WITHOUT_IMPORT_WITNESS'); self.assertFalse(r.complete)
    def test_invalid_kind(self): self.assertEqual(find_import_witness(self.initial,self.batches,kind=[]).status,'INVALID_IMPORT_WITNESS_KIND')
    def test_invalid_trace_shape(self):
        self.assertEqual(replay_import_witness(replace(self.witness,left=replace(self.left,statuses=()))).status,'INVALID_IMPORT_WITNESS_TRACE')
    def test_invalid_witness(self): self.assertEqual(replay_import_witness(None).status,'INVALID_IMPORT_WITNESS')
    def test_flags(self):
        r=replay_import_witness(self.witness); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
