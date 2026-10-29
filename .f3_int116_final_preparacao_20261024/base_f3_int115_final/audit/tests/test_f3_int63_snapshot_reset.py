import unittest
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int63_snapshot_reset_simulator import probe_reset, safe_to_promote


class ResetProbeTests(unittest.TestCase):
    def item(self,epoch=5,round_id='a'): return request(round_id,**recovery(epoch))
    def test_whole_reset_replay_demonstrated(self):
        r=probe_reset(Snapshot(),self.item())
        self.assertEqual(r.status,'CALLER_RESET_REPLAY_UNDETECTABLE_FIXTURE')
        self.assertEqual(dict(r.outcomes)['whole'],'COMMIT_FIXTURE_UNAUTHENTICATED')
    def test_held_snapshot_detects_replay(self):
        self.assertEqual(dict(probe_reset(Snapshot(),self.item()).outcomes)['none'],'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_only_version_reset_rejected(self):
        self.assertEqual(dict(probe_reset(Snapshot(),self.item()).outcomes)['version_only'],'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_only_state_reset_rejected(self):
        self.assertEqual(dict(probe_reset(Snapshot(),self.item()).outcomes)['state_only'],'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_original_not_mutated(self):
        s=Snapshot(); r=probe_reset(s,self.item()); self.assertEqual(s,Snapshot()); self.assertEqual(r.snapshot.version,1)
    def test_seeded_extension_reset(self):
        first=probe_reset(Snapshot(),self.item()).snapshot
        r=probe_reset(first,self.item(6,'b')); self.assertEqual(r.snapshot.state.memory.rounds,('a','b'))
        self.assertEqual(r.status,'CALLER_RESET_REPLAY_UNDETECTABLE_FIXTURE')
    def test_partial_probe_not_proof(self):
        r=probe_reset(Snapshot(),self.item(),modes=('none',))
        self.assertEqual(r.status,'PARTIAL_RESET_PROBE_FIXTURE_UNAUTHENTICATED')
    def test_rejected_recovery(self):
        bad=request('a',**dict(recovery(),partitioned=True))
        r=probe_reset(Snapshot(),bad); self.assertEqual(r.outcomes,()); self.assertEqual(r.snapshot,Snapshot())
    def test_invalid_modes(self):
        for modes in ((),[],('none','none'),('unknown',),(False,)):
            self.assertEqual(probe_reset(Snapshot(),self.item(),modes=modes).status,'INVALID_RESET_PROBE')
    def test_invalid_fixture(self):
        self.assertEqual(probe_reset(None,self.item()).status,'INVALID_RESET_PROBE')
        self.assertEqual(probe_reset(Snapshot(),None).status,'INVALID_RESET_PROBE')
    def test_order_independent_outcomes(self):
        a=probe_reset(Snapshot(),self.item()); b=probe_reset(Snapshot(),self.item(),modes=('whole','state_only','version_only','none'))
        self.assertEqual(dict(a.outcomes),dict(b.outcomes))
    def test_flags(self):
        r=probe_reset(Snapshot(),self.item()); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
