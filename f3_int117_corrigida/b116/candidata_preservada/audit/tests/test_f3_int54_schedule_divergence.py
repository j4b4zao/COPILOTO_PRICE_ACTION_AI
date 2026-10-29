import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot, prepare, commit
from tools.f3_int54_schedule_divergence_simulator import (
    request, explore, schedules, run_schedule, compare_shared, safe_to_promote, Request)


class ScheduleTests(unittest.TestCase):
    def reqs(self): return (request('a',**recovery()),request('b',**recovery()))
    def test_six_topological_orders(self):
        orders=tuple(schedules(2)); self.assertEqual(len(orders),6); self.assertEqual(len(set(orders)),6)
    def test_complete_at_exact_bound(self):
        r=explore(Snapshot(),self.reqs(),max_schedules=6)
        self.assertTrue(r.complete); self.assertEqual(r.checked,6)
    def test_bound_reports_incomplete(self):
        r=explore(Snapshot(),self.reqs(),max_schedules=5)
        self.assertFalse(r.complete); self.assertEqual(r.checked,5)
        self.assertEqual(r.status,'EXPLORATION_LIMIT_REACHED')
    def test_divergent_round_winners(self):
        r=explore(Snapshot(),self.reqs()); self.assertTrue(r.divergent)
        self.assertEqual({x.snapshots[-1].state.memory.rounds for x in r.runs},{('a',),('b',)})
    def test_branch_winners(self):
        r=explore(Snapshot(),(request('a',**recovery(pin='x')),request('b',**recovery(pin='y'))))
        self.assertEqual({x.snapshots[-1].state.memory.digest for x in r.runs},{'x','y'})
    def test_identical_proposals_terminal_equal(self):
        a=request('a',**recovery()); r=explore(Snapshot(),(a,a))
        self.assertTrue(r.complete); self.assertFalse(r.divergent)
    def test_single_actor(self):
        r=explore(Snapshot(),self.reqs()[:1]); self.assertEqual(r.checked,1); self.assertFalse(r.divergent)
    def test_rejected_proposals_do_not_mutate(self):
        a=request('a',**dict(recovery(),partitioned=True)); s=Snapshot(); r=explore(s,(a,a))
        self.assertTrue(all(x==s for run in r.runs for x in run.snapshots))
    def test_stale_commit_atomic(self):
        r=explore(Snapshot(),self.reqs())
        for run in r.runs:
            for i,status in enumerate(run.statuses):
                if status=='STALE_OR_CONFLICTING_SNAPSHOT': self.assertIs(run.snapshots[i],run.snapshots[i+1])
    def test_trace_length(self):
        for run in explore(Snapshot(),self.reqs()).runs:
            self.assertEqual((len(run.statuses),len(run.snapshots)),(4,5))
    def test_invalid_actor(self):
        with self.assertRaises(ValueError): run_schedule(Snapshot(),self.reqs(),(('prepare',True),)*4)
    def test_commit_before_prepare(self):
        with self.assertRaises(ValueError): run_schedule(Snapshot(),self.reqs(),(('commit',0),)*4)
    def test_duplicate_prepare(self):
        with self.assertRaises(ValueError): run_schedule(Snapshot(),self.reqs(),(('prepare',0),)*4)
    def test_short_schedule(self):
        with self.assertRaises(ValueError): run_schedule(Snapshot(),self.reqs(),())
    def test_bad_bounds(self):
        for bound in (False,0,-1,4097,'6'):
            self.assertEqual(explore(Snapshot(),self.reqs(),max_schedules=bound).status,'INVALID_EXPLORATION_BOUND')
    def test_request_limit(self):
        self.assertEqual(explore(Snapshot(),self.reqs()*3).status,'INVALID_EXPLORATION_FIXTURE')
    def test_request_mutable(self):
        self.assertEqual(explore(Snapshot(),(Request('a',[]),)).status,'INVALID_EXPLORATION_FIXTURE')
    def test_bad_initial(self):
        self.assertEqual(explore(None,self.reqs()).status,'INVALID_EXPLORATION_FIXTURE')
    def test_same_version_different_state(self):
        a=commit(Snapshot(),prepare(Snapshot(),'a',**recovery()).proposal).snapshot
        b=commit(Snapshot(),prepare(Snapshot(),'b',**recovery()).proposal).snapshot
        self.assertEqual(compare_shared((a,b)).status,'REPLICA_STATE_DIVERGENCE')
    def test_different_version(self):
        self.assertEqual(compare_shared((Snapshot(),Snapshot(1))).status,'REPLICA_VERSION_DIVERGENCE')
    def test_equal_replicas_untrusted(self):
        self.assertEqual(compare_shared((Snapshot(),Snapshot())).status,'EQUAL_REPLICA_FIXTURES_UNAUTHENTICATED')
    def test_replica_bounds(self):
        for values in ((),(Snapshot(),),[Snapshot(),Snapshot()],(Snapshot(),)*17,(None,None)):
            self.assertEqual(compare_shared(values).status,'INVALID_REPLICA_FIXTURE')
    def test_deterministic(self):
        self.assertEqual(explore(Snapshot(),self.reqs()),explore(Snapshot(),self.reqs()))
    def test_flags(self):
        for r in (explore(Snapshot(),self.reqs()),compare_shared((Snapshot(),Snapshot()))):
            self.assertEqual(r.f3,'OPEN')
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
            self.assertFalse(safe_to_promote(r))
