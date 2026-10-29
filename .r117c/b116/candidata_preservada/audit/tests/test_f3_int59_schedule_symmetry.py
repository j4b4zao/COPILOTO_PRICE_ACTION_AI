import unittest
from math import factorial
from test_f3_int53_interleaving import recovery
from tools.f3_int54_schedule_divergence_simulator import request, Request
from tools.f3_int59_schedule_symmetry_simulator import assess_symmetry, safe_to_promote


class SymmetryTests(unittest.TestCase):
    def reqs(self,n): return tuple(request(str(i),**recovery()) for i in range(n))
    def test_one_two_three_actor_families(self):
        for n in (1,2,3):
            r=assess_symmetry(self.reqs(n)); total=factorial(2*n)//2**n
            self.assertEqual(r.status,'SYMMETRY_FIXTURE_UNAUTHENTICATED')
            self.assertEqual(r.checked,total); self.assertTrue(r.complete)
            self.assertEqual(tuple(c for _,c in r.winner_counts),(total//n,)*n)
    def test_four_actor_2520_orders(self):
        r=assess_symmetry(self.reqs(4))
        self.assertEqual(r.checked,2520); self.assertTrue(r.complete)
        self.assertEqual(tuple(c for _,c in r.winner_counts),(630,)*4)
        self.assertEqual(r.f3,'OPEN')
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
        self.assertFalse(safe_to_promote(r))
    def test_incomplete_does_not_claim_symmetry(self):
        r=assess_symmetry(self.reqs(3),max_schedules=10)
        self.assertEqual(r.status,'SYMMETRY_EXPLORATION_INCOMPLETE'); self.assertFalse(r.complete)
    def test_duplicate_rounds(self):
        a=self.reqs(1)[0]; self.assertEqual(assess_symmetry((a,a)).status,'INVALID_SYMMETRY_FIXTURE')
    def test_asymmetric_arguments(self):
        args=(self.reqs(1)[0],request('b',**recovery(6)))
        self.assertEqual(assess_symmetry(args).status,'INVALID_SYMMETRY_FIXTURE')
    def test_invalid_recovery(self):
        a=request('a',**dict(recovery(),partitioned=True))
        self.assertEqual(assess_symmetry((a,)).status,'INVALID_SYMMETRY_FIXTURE')
    def test_invalid_actor_count(self):
        for args in ((),self.reqs(5),[],(None,)):
            self.assertEqual(assess_symmetry(args).status,'INVALID_SYMMETRY_FIXTURE')
    def test_adversarial_depth(self):
        value=()
        for _ in range(40): value=(value,)
        self.assertEqual(assess_symmetry((Request('a',(('votes',value),)),)).status,'INVALID_SYMMETRY_FIXTURE')
    def test_invalid_bound(self):
        self.assertEqual(assess_symmetry(self.reqs(2),max_schedules=False).status,'INVALID_EXPLORATION_BOUND')
