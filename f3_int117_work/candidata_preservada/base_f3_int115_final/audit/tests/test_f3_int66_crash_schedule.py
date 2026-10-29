import unittest
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int66_crash_schedule_simulator import run_crash_schedule, safe_to_promote


class CrashScheduleTests(unittest.TestCase):
    def reqs(self): return (request('a',**recovery(6)),request('b',**recovery(5)))
    def run_events(self,events,**kwargs): return run_crash_schedule(Snapshot(),self.reqs(),events,**kwargs)
    def test_normal_commit(self):
        r=self.run_events((('prepare',0,0),('commit',0,0))); self.assertEqual(r.snapshot.version,1)
    def test_crash_drops_pending(self):
        r=self.run_events((('prepare',0,0),('crash',0,0),('commit',0,1)))
        self.assertEqual(r.trace[-1][3],'NO_PENDING_PROPOSAL'); self.assertEqual(r.snapshot,Snapshot())
    def test_old_generation_rejected(self):
        r=self.run_events((('prepare',0,0),('crash',0,0),('commit',0,0)))
        self.assertEqual(r.trace[-1][3],'STALE_ACTOR_GENERATION'); self.assertEqual(r.snapshot,Snapshot())
    def test_restart_reprepare(self):
        r=self.run_events((('prepare',0,0),('crash',0,0),('prepare',0,1),('commit',0,1)))
        self.assertEqual(r.snapshot.version,1); self.assertEqual(r.generations,(1,0))
    def test_committed_snapshot_survives_actor_crash(self):
        r=self.run_events((('prepare',0,0),('commit',0,0),('crash',0,0)))
        self.assertEqual(r.snapshot.state.memory.rounds,('a',)); self.assertEqual(r.snapshot.version,1)
    def test_other_actor_pending_survives_crash(self):
        r=self.run_events((('prepare',1,0),('crash',0,0),('commit',1,0)))
        self.assertEqual(r.snapshot.state.memory.rounds,('b',))
    def test_competing_commit_stales_old_proposal(self):
        r=self.run_events((('prepare',0,0),('prepare',1,0),('commit',1,0),('commit',0,0)))
        self.assertEqual(r.trace[-1][3],'STALE_OR_CONFLICTING_SNAPSHOT'); self.assertEqual(r.snapshot.version,1)
    def test_restart_after_competing_commit(self):
        events=(('prepare',0,0),('crash',0,0),('prepare',1,0),('commit',1,0),('prepare',0,1),('commit',0,1))
        r=self.run_events(events); self.assertEqual(r.snapshot.state.memory.rounds,('b','a')); self.assertEqual(r.snapshot.version,2)
    def test_replay_round_after_crash(self):
        r=self.run_events((('prepare',0,0),('commit',0,0),('crash',0,0),('prepare',0,1)))
        self.assertEqual(r.trace[-1][3],'REPLAYED_ROUND')
    def test_duplicate_commit_no_pending(self):
        r=self.run_events((('prepare',0,0),('commit',0,0),('commit',0,0)))
        self.assertEqual(r.trace[-1][3],'NO_PENDING_PROPOSAL'); self.assertEqual(r.snapshot.version,1)
    def test_future_generation_rejected(self):
        r=self.run_events((('crash',0,1),)); self.assertEqual(r.generations,(0,0)); self.assertEqual(r.trace[0][3],'STALE_ACTOR_GENERATION')
    def test_malformed_tail_atomic(self):
        r=self.run_events((('prepare',0,0),('commit',0,0),('unknown',0,0)))
        self.assertEqual(r.status,'INVALID_CRASH_EVENT'); self.assertEqual(r.trace,()); self.assertEqual(r.snapshot,Snapshot())
    def test_invalid_event_bool_actor(self):
        self.assertEqual(self.run_events((('prepare',False,0),)).status,'INVALID_CRASH_EVENT')
    def test_invalid_event_bool_generation(self):
        self.assertEqual(self.run_events((('prepare',0,False),)).status,'INVALID_CRASH_EVENT')
    def test_event_limit(self):
        self.assertEqual(self.run_events((('crash',0,0),)*17).status,'INVALID_CRASH_FIXTURE')
    def test_invalid_bound(self):
        self.assertEqual(self.run_events((('crash',0,0),),max_events=False).status,'INVALID_CRASH_BOUND')
    def test_original_unchanged(self):
        s=Snapshot(); run_crash_schedule(s,self.reqs(),(('prepare',0,0),('commit',0,0))); self.assertEqual(s,Snapshot())
    def test_deterministic(self):
        events=(('prepare',0,0),('crash',0,0)); self.assertEqual(self.run_events(events),self.run_events(events))
    def test_flags(self):
        r=self.run_events((('prepare',0,0),('commit',0,0))); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
