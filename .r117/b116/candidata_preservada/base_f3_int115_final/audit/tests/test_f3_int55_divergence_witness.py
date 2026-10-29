import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import request, run_schedule
from tools.f3_int55_divergence_witness_simulator import Witness, replay, find_witness, safe_to_promote


class WitnessTests(unittest.TestCase):
    def reqs(self): return (request('a',**recovery()),request('b',**recovery()))
    def witness(self): return find_witness(Snapshot(),self.reqs()).witness
    def test_find(self):
        r=find_witness(Snapshot(),self.reqs()); self.assertTrue(r.complete); self.assertIsNotNone(r.witness)
        self.assertEqual(r.status,'DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED')
    def test_replay(self):
        w=self.witness(); self.assertEqual(replay(w).witness,w)
    def test_no_divergence(self):
        a=request('a',**recovery()); r=find_witness(Snapshot(),(a,a))
        self.assertEqual(r.status,'NO_DIVERGENCE_IN_EXPLORED_FIXTURES'); self.assertTrue(r.complete)
    def test_incomplete_not_proof(self):
        r=find_witness(Snapshot(),self.reqs(),max_schedules=1)
        self.assertEqual(r.status,'INCOMPLETE_WITHOUT_WITNESS'); self.assertFalse(r.complete)
    def test_partial_can_find_witness(self):
        r=find_witness(Snapshot(),self.reqs(),max_schedules=5)
        self.assertIsNotNone(r.witness); self.assertFalse(r.complete)
    def test_status_tampering(self):
        w=self.witness(); trace=replace(w.left,statuses=('forged',)+w.left.statuses[1:])
        self.assertEqual(replay(replace(w,left=trace)).status,'TRACE_REPLAY_MISMATCH')
    def test_intermediate_snapshot_tampering(self):
        w=self.witness(); trace=replace(w.left,snapshots=(Snapshot(99),)+w.left.snapshots[1:])
        self.assertEqual(replay(replace(w,left=trace)).status,'TRACE_REPLAY_MISMATCH')
    def test_terminal_snapshot_tampering(self):
        w=self.witness(); trace=replace(w.left,snapshots=w.left.snapshots[:-1]+(Snapshot(),))
        self.assertEqual(replay(replace(w,left=trace)).status,'TRACE_REPLAY_MISMATCH')
    def test_schedule_tampering(self):
        w=self.witness(); trace=replace(w.left,schedule=(('commit',0),)*4)
        self.assertEqual(replay(replace(w,left=trace)).status,'INVALID_TRACE_SCHEDULE')
    def test_truncated_statuses(self):
        w=self.witness(); self.assertEqual(replay(replace(w,left=replace(w.left,statuses=()))).status,'INVALID_TRACE_SHAPE')
    def test_truncated_snapshots(self):
        w=self.witness(); self.assertEqual(replay(replace(w,left=replace(w.left,snapshots=()))).status,'INVALID_TRACE_SHAPE')
    def test_mutable_trace(self):
        w=self.witness(); self.assertEqual(replay(replace(w,left=replace(w.left,statuses=list(w.left.statuses)))).status,'INVALID_TRACE_SHAPE')
    def test_initial_tampering(self):
        w=self.witness(); self.assertEqual(replay(replace(w,initial=Snapshot(7))).status,'TRACE_REPLAY_MISMATCH')
    def test_requests_tampering(self):
        w=self.witness(); args=(request('x',**recovery()),w.requests[1])
        self.assertEqual(replay(replace(w,requests=args)).status,'TRACE_REPLAY_MISMATCH')
    def test_identical_trace_no_divergence(self):
        w=self.witness(); self.assertEqual(replay(replace(w,right=w.left)).status,'NO_TERMINAL_DIVERGENCE')
    def test_invalid_witness(self): self.assertEqual(replay(None).status,'INVALID_WITNESS')
    def test_invalid_trace(self):
        w=self.witness(); self.assertEqual(replay(replace(w,left=None)).status,'INVALID_WITNESS')
    def test_invalid_bound(self):
        self.assertEqual(find_witness(Snapshot(),self.reqs(),max_schedules=False).status,'INVALID_EXPLORATION_BOUND')
    def test_deterministic_witness(self): self.assertEqual(self.witness(),self.witness())
    def test_flags(self):
        for r in (replay(self.witness()),replay(None),find_witness(Snapshot(),self.reqs(),max_schedules=1)):
            self.assertEqual(r.f3,'OPEN')
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
            self.assertFalse(safe_to_promote(r))
