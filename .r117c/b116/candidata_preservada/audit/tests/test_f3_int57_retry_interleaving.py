import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import request, Request
from tools.f3_int57_retry_interleaving_simulator import recover, safe_to_promote


class RetryTests(unittest.TestCase):
    def item(self,epoch=6,round_id='a'): return request(round_id,**recovery(epoch))
    def test_no_contender(self):
        r=recover(Snapshot(),self.item()); self.assertEqual(r.status,'RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(r.snapshot.state.memory.rounds,('a',))
    def test_rebase_after_competing_commit(self):
        r=recover(Snapshot(),self.item(),contenders=(self.item(5,'b'),))
        self.assertEqual(r.status,'RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual((r.snapshot.version,r.snapshot.state.memory.rounds),(2,('b','a')))
    def test_budget_exhaustion(self):
        r=recover(Snapshot(),self.item(),contenders=(self.item(5,'b'),),max_attempts=1)
        self.assertEqual(r.status,'RETRY_BUDGET_EXHAUSTED'); self.assertEqual(r.snapshot.state.memory.rounds,('b',))
    def test_replay_evidence_blocks_retry(self):
        r=recover(Snapshot(),self.item(5),contenders=(self.item(5,'b'),))
        self.assertEqual(r.status,'REPLAYED_CROSS_ROUND_EVIDENCE'); self.assertEqual(r.snapshot.version,1)
    def test_same_round_blocks_retry(self):
        r=recover(Snapshot(),self.item(),contenders=(self.item(5,'a'),))
        self.assertEqual(r.status,'REPLAYED_ROUND')
    def test_epoch_rollback_blocks_retry(self):
        r=recover(Snapshot(),self.item(5),contenders=(self.item(6,'b'),))
        self.assertEqual(r.status,'TRUNCATED_PREFIX')
    def test_rejected_contender(self):
        other=request('b',**dict(recovery(5),partitioned=True))
        r=recover(Snapshot(),self.item(),contenders=(other,))
        self.assertEqual(r.status,'RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.snapshot.version,1)
    def test_two_stale_attempts_then_success(self):
        r=recover(Snapshot(),self.item(7),contenders=(self.item(5,'b'),self.item(6,'c')),max_attempts=3)
        self.assertEqual(r.snapshot.state.memory.rounds,('b','c','a')); self.assertEqual(r.snapshot.version,3)
    def test_stale_trace_keeps_competing_snapshot(self):
        r=recover(Snapshot(),self.item(),contenders=(self.item(5,'b'),))
        self.assertEqual(r.trace[2][3],r.trace[3][3]); self.assertEqual(r.trace[3][2],'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_initial_unchanged(self):
        s=Snapshot(); recover(s,self.item(),contenders=(self.item(5,'b'),)); self.assertEqual(s,Snapshot())
    def test_invalid_bounds(self):
        for bound in (False,0,5,'2'):
            self.assertEqual(recover(Snapshot(),self.item(),max_attempts=bound).status,'INVALID_RETRY_BOUND')
    def test_unused_contenders_rejected(self):
        self.assertEqual(recover(Snapshot(),self.item(),contenders=(None,)*3).status,'INVALID_RETRY_FIXTURE')
    def test_mutable_contenders(self):
        self.assertEqual(recover(Snapshot(),self.item(),contenders=[]).status,'INVALID_RETRY_FIXTURE')
    def test_invalid_request(self):
        self.assertEqual(recover(Snapshot(),Request('a',[])).status,'INVALID_RETRY_FIXTURE')
    def test_deep_request_rejected(self):
        value=()
        for _ in range(40): value=(value,)
        self.assertEqual(recover(Snapshot(),Request('a',(('history',value),))).status,'INVALID_RETRY_FIXTURE')
    def test_invalid_initial(self):
        self.assertEqual(recover(None,self.item()).status,'INVALID_RETRY_FIXTURE')
    def test_deterministic(self):
        self.assertEqual(recover(Snapshot(),self.item()),recover(Snapshot(),self.item()))
    def test_flags(self):
        for r in (recover(Snapshot(),self.item()),recover(Snapshot(),None)):
            self.assertEqual(r.f3,'OPEN')
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
            self.assertFalse(safe_to_promote(r))
