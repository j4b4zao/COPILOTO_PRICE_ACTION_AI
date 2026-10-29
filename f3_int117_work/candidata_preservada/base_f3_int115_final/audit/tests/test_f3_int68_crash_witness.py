import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int68_crash_witness_simulator import find_crash_witness, replay_crash_witness, safe_to_promote


class CrashWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests=(request('a',**recovery(6)),request('b',**recovery(5)))
        cls.result=find_crash_witness(cls.requests)
        cls.witness=cls.result.witness
    def test_find(self):
        self.assertTrue(self.result.complete); self.assertEqual(self.result.checked,252)
        self.assertEqual(self.result.status,'CRASH_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED')
    def test_replay(self): self.assertEqual(replay_crash_witness(self.witness).witness,self.witness)
    def test_generation_tampering(self):
        w=self.witness; trace=replace(w.left,generations=(9,9))
        self.assertEqual(replay_crash_witness(replace(w,left=trace)).status,'CRASH_TRACE_REPLAY_MISMATCH')
    def test_final_snapshot_tampering(self):
        w=self.witness; trace=replace(w.left,snapshot=replace(w.left.snapshot,version=99))
        self.assertEqual(replay_crash_witness(replace(w,left=trace)).status,'CRASH_TRACE_REPLAY_MISMATCH')
    def test_row_status_tampering(self):
        w=self.witness; first=w.left.trace[0]; row=first[:3]+('forged',)+first[4:]
        trace=replace(w.left,trace=(row,)+w.left.trace[1:])
        self.assertEqual(replay_crash_witness(replace(w,left=trace)).status,'CRASH_TRACE_REPLAY_MISMATCH')
    def test_flag_tampering(self):
        w=self.witness; trace=replace(w.left,orders_allowed=True)
        self.assertEqual(replay_crash_witness(replace(w,left=trace)).status,'CRASH_TRACE_REPLAY_MISMATCH')
    def test_identical_trace(self):
        w=self.witness; self.assertEqual(replay_crash_witness(replace(w,right=w.left)).status,'NO_CRASH_TERMINAL_DIVERGENCE')
    def test_incomplete_no_proof(self):
        r=find_crash_witness(self.requests,max_schedules=1)
        self.assertEqual(r.status,'INCOMPLETE_WITHOUT_CRASH_WITNESS'); self.assertFalse(r.complete)
    def test_identical_requests_no_divergence(self):
        a=request('a',**recovery(5)); r=find_crash_witness((a,a))
        self.assertEqual(r.status,'NO_CRASH_DIVERGENCE_IN_EXPLORED_FIXTURES'); self.assertTrue(r.complete)
    def test_invalid_witness(self): self.assertEqual(replay_crash_witness(None).status,'INVALID_CRASH_WITNESS')
    def test_invalid_trace(self):
        w=self.witness; self.assertEqual(replay_crash_witness(replace(w,left=replace(w.left,trace=()))).status,'INVALID_CRASH_WITNESS_TRACE')
    def test_flags(self):
        r=replay_crash_witness(self.witness); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
