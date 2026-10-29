import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import request, Request
from tools.f3_int58_bounded_exploration_simulator import bounded_explore, bounded_find, bounded_replay, safe_to_promote


class BoundedExplorationTests(unittest.TestCase):
    def reqs(self): return (request('a',**recovery()),request('b',**recovery()))
    def witness(self): return bounded_find(Snapshot(),self.reqs()).witness
    def test_explore(self):
        r=bounded_explore(Snapshot(),self.reqs()); self.assertTrue(r.complete); self.assertTrue(r.divergent)
    def test_find_replay(self):
        w=self.witness(); self.assertIsNotNone(w); self.assertEqual(bounded_replay(w).witness,w)
    def test_deep_requests(self):
        value=()
        for _ in range(40): value=(value,)
        reqs=(Request('a',(('votes',value),)),)
        self.assertEqual(bounded_explore(Snapshot(),reqs).status,'INPUT_DEPTH_LIMIT')
        self.assertEqual(bounded_find(Snapshot(),reqs).status,'INPUT_DEPTH_LIMIT')
    def test_mutable_requests(self):
        self.assertEqual(bounded_explore(Snapshot(),list(self.reqs())).status,'INVALID_EXPLORATION_FIXTURE')
    def test_unknown_request(self):
        self.assertEqual(bounded_find(Snapshot(),(object(),)).status,'INVALID_EXPLORATION_FIXTURE')
    def test_oversized_requests(self):
        self.assertEqual(bounded_explore(Snapshot(),self.reqs()*3).status,'INVALID_EXPLORATION_FIXTURE')
    def test_node_limit(self):
        self.assertEqual(bounded_explore(Snapshot(),self.reqs(),bounds={'max_nodes':4}).status,'INPUT_NODE_LIMIT')
    def test_string_limit(self):
        reqs=(request('x'*4097,**recovery()),)
        self.assertEqual(bounded_find(Snapshot(),reqs).status,'INPUT_STRING_LIMIT')
    def test_bad_bounds(self):
        for call in (bounded_explore,bounded_find):
            self.assertEqual(call(Snapshot(),self.reqs(),bounds=[]).status,'INVALID_INGESTION_BOUND')
    def test_schedule_limit(self):
        self.assertFalse(bounded_explore(Snapshot(),self.reqs(),max_schedules=1).complete)
    def test_deep_trace(self):
        value=()
        for _ in range(40): value=(value,)
        w=self.witness(); w=replace(w,left=replace(w.left,schedule=value))
        self.assertEqual(bounded_replay(w).status,'INPUT_DEPTH_LIMIT')
    def test_mutable_trace(self):
        w=self.witness(); w=replace(w,left=replace(w.left,statuses=[]))
        self.assertEqual(bounded_replay(w).status,'MUTABLE_OR_UNKNOWN_INPUT')
    def test_large_trace(self):
        w=self.witness(); w=replace(w,left=replace(w.left,statuses=('x',)*5000))
        self.assertEqual(bounded_replay(w).status,'INPUT_NODE_LIMIT')
    def test_bad_witness(self): self.assertEqual(bounded_replay(None).status,'INVALID_WITNESS')
    def test_replay_bad_bounds(self):
        self.assertEqual(bounded_replay(self.witness(),bounds=[]).status,'INVALID_INGESTION_BOUND')
    def test_replay_tampering(self):
        w=self.witness(); w=replace(w,left=replace(w.left,statuses=('x',)*4))
        self.assertEqual(bounded_replay(w).status,'TRACE_REPLAY_MISMATCH')
    def test_deterministic(self):
        self.assertEqual(bounded_explore(Snapshot(),self.reqs()),bounded_explore(Snapshot(),self.reqs()))
    def test_flags(self):
        for r in (bounded_explore(Snapshot(),self.reqs()),bounded_replay(self.witness())):
            self.assertEqual(r.f3,'OPEN')
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
            self.assertFalse(safe_to_promote(r))
