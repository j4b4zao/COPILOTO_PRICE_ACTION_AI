import unittest
from dataclasses import replace
from test_f3_int78_verified_envelope import rewrite_record
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int78_verified_envelope import EnvelopePolicy
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot
from tools.f3_int84_import_schedule_divergence import explore_imports
from tools.f3_int86_policy_bound_import import PolicySnapshot
from tools.f3_int95_policy_import_schedules import explore_policy_imports,run_policy_schedule,safe_to_promote


class PolicyScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=import_requests('a','b'); cls.b=import_requests('c','d',1)
        request=cls.a[0]; package=rewrite_record(request.record,{f'docs/extra{i}':b'x' for i in range(600)})
        cls.large=(replace(request,record=package),)
    def test_default_policy_matches_original_endings(self):
        old=explore_imports(RegistrySnapshot(),(self.a,self.b)); new=explore_policy_imports(PolicySnapshot(),(self.a,self.b))
        self.assertEqual(tuple((r.snapshots[-1].version,r.snapshots[-1].registry) for r in old.runs),
                         tuple((r.snapshots[-1].version,r.snapshots[-1].registry) for r in new.runs))
    def test_large_package_explicit_policy(self):
        r=explore_policy_imports(PolicySnapshot(policy=EnvelopePolicy(1024)),(self.large,self.b))
        self.assertTrue(r.complete); self.assertTrue(r.content_divergence)
        self.assertEqual(len({x.snapshots[-1].registry.digests for x in r.runs}),4)
    def test_default_policy_rejects_large_actor(self):
        r=explore_policy_imports(PolicySnapshot(),(self.large,self.b))
        self.assertFalse(r.content_divergence); self.assertEqual({len(x.snapshots[-1].registry.digests) for x in r.runs},{1})
    def test_policy_remains_identical(self):
        s=PolicySnapshot(); r=explore_policy_imports(s,(self.a,self.b),max_schedules=2)
        for run in r.runs:
            for snapshot in run.snapshots: self.assertIs(snapshot.policy,s.policy)
    def test_incomplete_coverage(self):
        r=explore_policy_imports(PolicySnapshot(),(self.a,self.b),max_schedules=1)
        self.assertFalse(r.complete); self.assertEqual(r.status,'POLICY_EXPLORATION_LIMIT_REACHED')
    def test_malformed_tail_rejected(self):
        with self.assertRaises(ValueError): run_policy_schedule(PolicySnapshot(),(self.a,self.b),(('prepare',0),('commit',0),('prepare',1),('unknown',1)))
    def test_unknown_operation_not_compared(self):
        class Hostile:
            def __eq__(self,other): raise AssertionError('comparison must not run')
        with self.assertRaises(ValueError): run_policy_schedule(PolicySnapshot(),(self.a,),((Hostile(),0),('commit',0)))
    def test_invalid_bound(self):
        self.assertEqual(explore_policy_imports(PolicySnapshot(),(self.a,),max_schedules=True).status,'INVALID_POLICY_EXPLORATION_BOUND')
    def test_flags(self):
        r=explore_policy_imports(PolicySnapshot(),(self.a,),max_schedules=1)
        self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
