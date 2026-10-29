import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot, prepare, commit
from tools.f3_int54_schedule_divergence_simulator import explore, request
from tools.f3_int64_transition_monitor_simulator import assess_transition, safe_to_promote


class MonitorTests(unittest.TestCase):
    def committed(self,initial=None,epoch=5,round_id='a'):
        s=initial or Snapshot(); return commit(s,prepare(s,round_id,**recovery(epoch)).proposal).snapshot
    def altered(self,**changes):
        after=self.committed(); return replace(after,state=replace(after.state,memory=replace(after.state.memory,**changes)))
    def check(self,before,after,expected,**kwargs):
        r=assess_transition(before,after,'COMMIT_FIXTURE_UNAUTHENTICATED',**kwargs); self.assertEqual(r.status,expected); return r
    def test_valid_bootstrap(self): self.check(Snapshot(),self.committed(),'NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED')
    def test_valid_extension(self):
        a=self.committed(); self.check(a,self.committed(a,6,'b'),'NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED')
    def test_all_two_actor_trace_transitions(self):
        reqs=(request('a',**recovery()),request('b',**recovery()))
        for run in explore(Snapshot(),reqs).runs:
            for i,(op,actor) in enumerate(run.schedule):
                r=assess_transition(run.snapshots[i],run.snapshots[i+1],run.statuses[i],operation=op)
                self.assertIn(r.status,('NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED','UNCHANGED_TRANSITION_FIXTURE_UNAUTHENTICATED'))
    def test_rejection_mutation(self):
        r=assess_transition(Snapshot(),self.committed(),'STALE_OR_CONFLICTING_SNAPSHOT')
        self.assertEqual(r.status,'REJECTION_OR_PREPARE_MUTATED_SNAPSHOT')
    def test_unchanged_rejection(self):
        s=Snapshot(); self.assertEqual(assess_transition(s,s,'STALE_OR_CONFLICTING_SNAPSHOT').status,'UNCHANGED_TRANSITION_FIXTURE_UNAUTHENTICATED')
    def test_version_not_incremented(self): self.check(Snapshot(),replace(self.committed(),version=0),'VERSION_INCREMENT_VIOLATION')
    def test_version_jump(self): self.check(Snapshot(),replace(self.committed(),version=2),'VERSION_INCREMENT_VIOLATION')
    def test_prepare_forged_commit_status(self): self.check(Snapshot(),self.committed(),'COMMIT_STATUS_ON_PREPARE',operation='prepare')
    def test_round_not_appended(self): self.check(Snapshot(),self.altered(rounds=()),'ROUND_APPEND_VIOLATION')
    def test_evidence_not_appended(self): self.check(Snapshot(),self.altered(consumed=()),'EVIDENCE_APPEND_VIOLATION')
    def test_prefix_rewrite(self):
        a=self.committed(); b=self.committed(a,6,'b'); bad=replace(b,state=replace(b.state,votes=()))
        self.check(a,bad,'CONTINUITY_PREFIX_VIOLATION')
    def test_epoch_rollback(self):
        a=self.committed(); b=self.committed(a,6,'b'); bad=replace(b,state=replace(b.state,memory=replace(b.state.memory,epoch=4)))
        self.check(a,bad,'MEMORY_EPOCH_ROLLBACK')
    def test_same_epoch_pin_change(self):
        a=self.committed(); b=self.committed(a,6,'b'); bad=replace(b,state=replace(b.state,memory=replace(b.state.memory,epoch=5,digest='other')))
        self.check(a,bad,'SAME_EPOCH_PIN_MUTATION')
    def test_invalid_snapshot(self): self.check(None,Snapshot(),'INVALID_MONITOR_FIXTURE')
    def test_unknown_nested_state(self):
        bad=replace(Snapshot(),state=replace(Snapshot().state,memory=object()))
        self.check(bad,Snapshot(),'MUTABLE_OR_UNKNOWN_INPUT')
    def test_invariant_preserving_forgery_limit(self):
        # Monitor only checks necessary transitions, not witness authentication.
        after=self.altered(digest='caller_forged_digest')
        self.check(Snapshot(),after,'NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED')
        self.assertFalse(safe_to_promote(after))
    def test_flags(self):
        r=self.check(Snapshot(),self.committed(),'NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
