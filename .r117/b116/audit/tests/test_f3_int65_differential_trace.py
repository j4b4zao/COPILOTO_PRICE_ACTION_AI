import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int58_bounded_exploration_simulator import bounded_find
from tools.f3_int65_differential_trace_simulator import assess_witness, safe_to_promote


class DifferentialTests(unittest.TestCase):
    def witness(self): return bounded_find(Snapshot(),(request('a',**recovery()),request('b',**recovery()))).witness
    def test_valid(self):
        r=assess_witness(self.witness()); self.assertEqual(r.status,'REPLAY_AND_NECESSARY_INVARIANTS_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.checked,8)
    def test_invariant_preserving_forgery(self):
        w=self.witness(); states=tuple(replace(s,state=replace(s.state,memory=replace(s.state.memory,digest='forged')))
                                     if s.version else s for s in w.left.snapshots)
        r=assess_witness(replace(w,left=replace(w.left,snapshots=states)))
        self.assertEqual(r.status,'NECESSARY_INVARIANTS_INSUFFICIENT_FIXTURE')
        self.assertEqual(r.replay_status,'TRACE_REPLAY_MISMATCH'); self.assertEqual(r.violations,())
    def test_version_jump_detected(self):
        w=self.witness(); states=tuple(replace(s,version=s.version+1) if s.version else s for s in w.left.snapshots)
        r=assess_witness(replace(w,left=replace(w.left,snapshots=states)))
        self.assertEqual(r.status,'TRANSITION_MONITOR_VIOLATION_FIXTURE')
        self.assertIn((0,1,'VERSION_INCREMENT_VIOLATION'),r.violations)
    def test_rejection_mutation_detected(self):
        w=self.witness(); states=w.left.snapshots[:-1]+(Snapshot(9),)
        r=assess_witness(replace(w,left=replace(w.left,snapshots=states)))
        self.assertEqual(r.status,'TRANSITION_MONITOR_VIOLATION_FIXTURE')
    def test_status_only_forgery(self):
        w=self.witness(); statuses=w.left.statuses[:-1]+('UNKNOWN_REJECTION',)
        r=assess_witness(replace(w,left=replace(w.left,statuses=statuses)))
        self.assertEqual(r.status,'NECESSARY_INVARIANTS_INSUFFICIENT_FIXTURE')
    def test_equal_traces(self):
        w=self.witness(); r=assess_witness(replace(w,right=w.left))
        self.assertEqual(r.replay_status,'NO_TERMINAL_DIVERGENCE')
        self.assertEqual(r.status,'NECESSARY_INVARIANTS_INSUFFICIENT_FIXTURE')
    def test_bad_witness(self): self.assertEqual(assess_witness(None).status,'INVALID_DIFFERENTIAL_FIXTURE')
    def test_bad_trace_shape(self):
        w=self.witness(); self.assertEqual(assess_witness(replace(w,left=replace(w.left,statuses=()))).status,'INVALID_DIFFERENTIAL_TRACE')
    def test_mutable_snapshots(self):
        w=self.witness(); self.assertEqual(assess_witness(replace(w,left=replace(w.left,snapshots=[]))).status,'INVALID_DIFFERENTIAL_TRACE')
    def test_oversized_trace(self):
        w=self.witness(); self.assertEqual(assess_witness(replace(w,left=replace(w.left,schedule=(('prepare',0),)*10))).status,'INVALID_DIFFERENTIAL_TRACE')
    def test_unknown_action(self):
        w=self.witness(); schedule=(('unknown',0),)+w.left.schedule[1:]
        self.assertEqual(assess_witness(replace(w,left=replace(w.left,schedule=schedule))).status,'INVALID_DIFFERENTIAL_TRACE')
    def test_flags(self):
        r=assess_witness(self.witness()); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
