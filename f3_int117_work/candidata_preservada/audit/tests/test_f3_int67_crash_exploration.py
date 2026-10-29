import unittest
from math import factorial
from test_f3_int53_interleaving import recovery
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int64_transition_monitor_simulator import assess_transition
from tools.f3_int67_crash_exploration_simulator import explore_crashes, interleavings, safe_to_promote


class CrashExplorationTests(unittest.TestCase):
    def reqs(self,n=2): return tuple(request(str(i),**recovery(6-i)) for i in range(n))
    def test_252_two_actor_orders(self):
        r=explore_crashes(self.reqs()); self.assertTrue(r.complete)
        self.assertEqual(r.checked,factorial(10)//factorial(5)**2)
        self.assertEqual(len({run.trace for run in r.runs}),252)
        for run in r.runs:
            before=Snapshot(); expected_generations=[0,0]
            for op,actor,generation,status,after,generations in run.trace:
                if op=='crash': expected_generations[actor]+=1
                self.assertEqual(generations,tuple(expected_generations))
                if op=='commit' and generation==0:
                    self.assertEqual(status,'STALE_ACTOR_GENERATION'); self.assertEqual(before,after)
                verdict=assess_transition(before,after,status,operation='commit' if op=='commit' else 'prepare')
                self.assertIn(verdict.status,('NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED','UNCHANGED_TRANSITION_FIXTURE_UNAUTHENTICATED'))
                before=after
            self.assertEqual(run.generations,(1,1))
    def test_single_actor(self):
        r=explore_crashes(self.reqs(1)); self.assertEqual(r.checked,1); self.assertTrue(r.complete)
        self.assertEqual(r.runs[0].snapshot.state.memory.rounds,('0',))
    def test_exact_bound_complete(self):
        self.assertTrue(explore_crashes(self.reqs(),max_schedules=252).complete)
    def test_one_below_bound_incomplete(self):
        r=explore_crashes(self.reqs(),max_schedules=251); self.assertFalse(r.complete); self.assertEqual(r.checked,251)
    def test_three_actor_budget(self):
        r=explore_crashes(self.reqs(3),max_schedules=16)
        self.assertFalse(r.complete); self.assertEqual(r.checked,16)
        self.assertEqual(r.status,'CRASH_EXPLORATION_LIMIT_REACHED')
    def test_invalid_actor_counts(self):
        for count in (False,0,4):
            with self.assertRaises(ValueError): next(interleavings(count))
    def test_invalid_input(self):
        for reqs in ((),[],(None,),self.reqs()*2):
            self.assertEqual(explore_crashes(reqs).status,'INVALID_CRASH_EXPLORATION_FIXTURE')
    def test_invalid_budget(self):
        for bound in (False,0,513): self.assertEqual(explore_crashes(self.reqs(),max_schedules=bound).status,'INVALID_CRASH_EXPLORATION_BOUND')
    def test_flags(self):
        r=explore_crashes(self.reqs(1)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for item in (r,)+r.runs:
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(item,k),False)
