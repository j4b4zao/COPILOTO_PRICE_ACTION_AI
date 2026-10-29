import unittest
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot
from tools.f3_int84_import_schedule_divergence import explore_imports,run_import_schedule,safe_to_promote


class ImportScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=import_requests('a','b'); cls.b=import_requests('c','d',1)
    def test_six_schedules_disjoint_batches(self):
        r=explore_imports(RegistrySnapshot(),(self.a,self.b)); self.assertTrue(r.complete); self.assertEqual(r.checked,6)
        self.assertTrue(r.ordered_divergence); self.assertTrue(r.content_divergence)
        endings={run.snapshots[-1].registry.digests for run in r.runs}
        self.assertEqual(len(endings),4); self.assertEqual({len(x) for x in endings},{1,2})
    def test_order_only_difference_when_serial(self):
        initial=RegistrySnapshot(); batches=(self.a,self.b)
        a=run_import_schedule(initial,batches,(('prepare',0),('commit',0),('prepare',1),('commit',1)))
        b=run_import_schedule(initial,batches,(('prepare',1),('commit',1),('prepare',0),('commit',0)))
        self.assertNotEqual(a.snapshots[-1].registry.digests,b.snapshots[-1].registry.digests)
        self.assertEqual(set(a.snapshots[-1].registry.digests),set(b.snapshots[-1].registry.digests))
    def test_duplicate_witness_converges_only_in_fixture(self):
        r=explore_imports(RegistrySnapshot(),(self.a,self.a))
        self.assertTrue(r.complete); self.assertFalse(r.ordered_divergence); self.assertFalse(r.content_divergence)
    def test_three_actors_bounded_prefix(self):
        r=explore_imports(RegistrySnapshot(),(self.a,self.b,self.a),max_schedules=3)
        self.assertFalse(r.complete); self.assertEqual(r.checked,3); self.assertEqual(r.status,'IMPORT_EXPLORATION_LIMIT_REACHED')
    def test_stale_commit_preserves_snapshot(self):
        for run in explore_imports(RegistrySnapshot(),(self.a,self.b)).runs:
            for i,status in enumerate(run.statuses):
                if status=='STALE_IMPORT_SNAPSHOT': self.assertIs(run.snapshots[i],run.snapshots[i+1])
    def test_invalid_order(self):
        with self.assertRaises(ValueError): run_import_schedule(RegistrySnapshot(),(self.a,self.b),(('commit',0),)*4)
    def test_bool_actor(self):
        with self.assertRaises(ValueError): run_import_schedule(RegistrySnapshot(),(self.a,self.b),(('prepare',False),)*4)
    def test_invalid_bounds(self):
        for bound in (False,0,91):
            self.assertEqual(explore_imports(RegistrySnapshot(),(self.a,),max_schedules=bound).status,'INVALID_IMPORT_EXPLORATION_BOUND')
    def test_invalid_batches(self):
        for batches in ((),[],(None,),(self.a,)*4):
            self.assertEqual(explore_imports(RegistrySnapshot(),batches).status,'INVALID_IMPORT_EXPLORATION_FIXTURE')
    def test_flags(self):
        r=explore_imports(RegistrySnapshot(),(self.a,self.b)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
