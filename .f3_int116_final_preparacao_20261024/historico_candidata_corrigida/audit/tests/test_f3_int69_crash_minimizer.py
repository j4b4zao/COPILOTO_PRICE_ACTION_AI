import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int68_crash_witness_simulator import find_crash_witness, replay_crash_witness
from tools.f3_int69_crash_minimizer_simulator import minimize_crash_witness, retains_crash_divergence, safe_to_promote


class CrashMinimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests=(request('a',**recovery(6)),request('b',**recovery(5)))
        cls.original=find_crash_witness(cls.requests).witness
        cls.result=minimize_crash_witness(cls.original)
    def events(self,w): return [tuple(row[:3] for row in t.trace) for t in (w.left,w.right)]
    def test_reduced(self):
        self.assertTrue(self.result.one_minimal)
        self.assertLess(sum(map(len,self.events(self.result.witness))),sum(map(len,self.events(self.original))))
    def test_replay_reduced(self):
        self.assertEqual(replay_crash_witness(self.result.witness).status,'CRASH_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED')
    def test_one_event_minimal(self):
        events=self.events(self.result.witness)
        for side in range(2):
            for i in range(len(events[side])):
                candidate=events.copy(); candidate[side]=candidate[side][:i]+candidate[side][i+1:]
                self.assertFalse(retains_crash_divergence(self.requests,*candidate))
    def test_predicate_retained(self):
        self.assertTrue(retains_crash_divergence(self.requests,*self.events(self.result.witness)))
    def test_limit_not_minimal(self):
        r=minimize_crash_witness(self.original,max_checks=1)
        self.assertFalse(r.one_minimal); self.assertEqual(r.status,'CRASH_MINIMIZATION_LIMIT_REACHED'); self.assertEqual(r.checked,1)
    def test_original_unchanged(self):
        self.assertEqual(tuple(map(len,self.events(self.original))),(10,10))
    def test_deterministic(self): self.assertEqual(self.result,minimize_crash_witness(self.original))
    def test_invalid_budget(self):
        for bound in (False,0,2049): self.assertEqual(minimize_crash_witness(self.original,max_checks=bound).status,'INVALID_MINIMIZATION_BOUND')
    def test_invalid_witness(self): self.assertEqual(minimize_crash_witness(None).status,'INVALID_CRASH_WITNESS')
    def test_tampered_input_rejected(self):
        w=self.original; bad=replace(w,left=replace(w.left,checked=999))
        self.assertEqual(minimize_crash_witness(bad).status,'CRASH_TRACE_REPLAY_MISMATCH')
    def test_no_stale_event_not_same_predicate(self):
        events=[tuple(e for e in side if not (e[0]=='commit' and e[2]==0)) for side in self.events(self.original)]
        self.assertFalse(retains_crash_divergence(self.requests,*events))
    def test_flags(self):
        r=self.result; self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
