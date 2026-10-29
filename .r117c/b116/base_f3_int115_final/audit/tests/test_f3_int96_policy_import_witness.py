import unittest
from dataclasses import replace
from test_f3_int78_verified_envelope import rewrite_record
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int78_verified_envelope import EnvelopePolicy
from tools.f3_int86_policy_bound_import import PolicySnapshot
from tools.f3_int95_policy_import_schedules import run_policy_schedule
from tools.f3_int96_policy_import_witness import PolicyImportWitness,replay_policy_witness,find_policy_witness,safe_to_promote


def policy_witness_fixture():
    a=import_requests('a','b'); b=import_requests('c','d',1)
    first=a[0]; large=rewrite_record(first.record,{f'docs/large{i}':b'x' for i in range(600)})
    batches=((replace(first,record=large),),b); initial=PolicySnapshot(policy=EnvelopePolicy(1024))
    left=run_policy_schedule(initial,batches,(('prepare',0),('commit',0),('prepare',1),('commit',1)))
    right=run_policy_schedule(initial,batches,(('prepare',1),('commit',1),('prepare',0),('commit',0)))
    return PolicyImportWitness(initial,batches,left,right)


class PolicyWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.witness=policy_witness_fixture()
    def test_large_policy_witness_replays(self):
        r=replay_policy_witness(self.witness); self.assertEqual(r.status,'POLICY_IMPORT_DIVERGENCE_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.classification,'ORDER_ONLY')
    def test_policy_field_tampering(self):
        w=self.witness; changed=replace(w.left.snapshots[-1],policy=EnvelopePolicy())
        trace=replace(w.left,snapshots=w.left.snapshots[:-1]+(changed,))
        self.assertEqual(replay_policy_witness(replace(w,left=trace)).status,'POLICY_WITNESS_CONTEXT_MISMATCH')
    def test_entire_policy_context_tampering(self):
        w=self.witness; policy=EnvelopePolicy()
        def changed(trace): return replace(trace,snapshots=tuple(replace(s,policy=policy) for s in trace.snapshots))
        bad=replace(w,initial=replace(w.initial,policy=policy),left=changed(w.left),right=changed(w.right))
        self.assertEqual(replay_policy_witness(bad).status,'POLICY_WITNESS_REPLAY_MISMATCH')
    def test_status_tampering(self):
        w=self.witness; bad=replace(w.left,statuses=('forged',)+w.left.statuses[1:])
        self.assertEqual(replay_policy_witness(replace(w,left=bad)).status,'POLICY_WITNESS_REPLAY_MISMATCH')
    def test_identical_traces(self):
        w=self.witness; self.assertEqual(replay_policy_witness(replace(w,right=w.left)).status,'NO_POLICY_IMPORT_TERMINAL_DIVERGENCE')
    def test_partial_search(self):
        w=self.witness; r=find_policy_witness(w.initial,w.batches,max_schedules=1)
        self.assertFalse(r.complete); self.assertEqual(r.status,'INCOMPLETE_WITHOUT_POLICY_WITNESS')
    def test_invalid_witness(self): self.assertEqual(replay_policy_witness(None).status,'INVALID_POLICY_IMPORT_WITNESS')
    def test_invalid_shape(self):
        w=self.witness; self.assertEqual(replay_policy_witness(replace(w,left=replace(w.left,statuses=()))).status,'INVALID_POLICY_WITNESS_TRACE')
    def test_flags(self):
        r=replay_policy_witness(self.witness); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
