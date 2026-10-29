import unittest
from tools.f3_int41_worker_handoff_simulator import Transfer as T, assess_transfers
from tools.f3_int42_adversarial_handoff_simulator import compare_views, safe_to_promote

class AdversarialHandoffTests(unittest.TestCase):
    def setUp(self):
        self.a=T('ACQUIRE','a',1,0,'t1')
        self.rel=T('RELEASE','a',1,1,'r1')
        self.b=T('ACQUIRE','b',2,1,'t2')
        self.c=T('ACQUIRE','c',2,1,'t3')
        self.left=(self.a,self.rel,self.b)
        self.right=(self.a,self.rel,self.c)
    def check(self,status,left=None,right=None,pin=None):
        result=compare_views(self.left if left is None else left,self.right if right is None else right,pin)
        self.assertEqual(result.status,status)
        self.assertFalse(result.authenticated or result.authoritative or result.closure_authorized)
        self.assertFalse(safe_to_promote(result))
        return result
    def test_fork_with_shared_pin(self): self.check('DIVERGENT_VALID_LOCAL_HISTORIES',pin=(1,self.a))
    def test_fork_pinned_to_left(self): self.check('PIN_CONFLICT',pin=(3,self.b))
    def test_fork_pinned_to_right(self): self.check('PIN_CONFLICT',pin=(3,self.c))
    def test_no_pin_fails_closed(self): self.check('MISSING_INDEPENDENT_REFERENCE')
    def test_invalid_pin(self): self.check('INVALID_PIN',pin=(True,self.a))
    def test_future_pin(self): self.check('PIN_UNAVAILABLE_IN_VIEW',pin=(4,self.b))
    def test_identical_history_not_authenticated(self): self.check('IDENTICAL_PINNED_FIXTURE_NOT_AUTHENTICATED',right=self.left,pin=(3,self.b))
    def test_prefix_uncertain(self): self.check('PREFIX_UNCERTAIN',right=self.left+(T('WRITE','b',2,2,'w'),),pin=(1,self.a))
    def test_forged_release_accepted_locally_not_authenticated(self):
        forged=(self.a,T('RELEASE','a',1,1,'forged'),self.c)
        self.assertTrue(assess_transfers(forged).fixture_consistent)
        self.check('DIVERGENT_VALID_LOCAL_HISTORIES',right=forged,pin=(1,self.a))
    def test_forged_acquire_token_locally_consistent(self):
        forged=(self.a,self.rel,T('ACQUIRE','b',2,1,'attacker-token'))
        self.assertTrue(assess_transfers(forged).fixture_consistent)
        self.check('DIVERGENT_VALID_LOCAL_HISTORIES',right=forged,pin=(1,self.a))
    def test_invalid_local_view(self): self.check('INVALID_LOCAL_VIEW',right=(self.a,self.b),pin=(1,self.a))
    def test_missing_or_malformed_view(self): self.check('INVALID_VIEW',left=None if False else 123,pin=(1,self.a))
    def test_no_pin_even_identical(self): self.check('MISSING_INDEPENDENT_REFERENCE',right=self.left)
    def test_pin_mismatch_both(self): self.check('PIN_CONFLICT',pin=(1,T('ACQUIRE','x',1,0,'fake')))

if __name__=='__main__': unittest.main()
