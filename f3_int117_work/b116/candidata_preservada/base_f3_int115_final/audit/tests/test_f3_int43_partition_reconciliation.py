import unittest
from tools.f3_int41_worker_handoff_simulator import Transfer as T
from tools.f3_int43_partition_reconciliation_simulator import Witness, reconcile_partition, safe_to_promote

class PartitionReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.a = T('ACQUIRE','a',1,0,'a1')
        self.r = T('RELEASE','a',1,1,'r1')
        self.b = T('ACQUIRE','b',2,1,'b2')
        self.c = T('ACQUIRE','c',2,1,'c2')
        self.left = (self.a,self.r,self.b)
        self.right = (self.a,self.r,self.c)
        self.w = (Witness('w1',1,self.a,True),Witness('w2',2,self.r,True))
    def check(self, expected, left=None, right=None, witnesses=None):
        result = reconcile_partition(self.left if left is None else left,
                                     self.right if right is None else right,
                                     self.w if witnesses is None else witnesses)
        self.assertEqual(result.status,expected)
        self.assertFalse(result.authenticated or result.authoritative or result.closure_authorized or result.witness_verified)
        self.assertFalse(safe_to_promote(result))
    def test_fork_with_common_witnesses(self): self.check('PARTITION_FORK_CONTESTED')
    def test_no_witness(self): self.check('NO_WITNESS',witnesses=())
    def test_agreement_not_authentication(self): self.check('AGREED_FIXTURE_UNAUTHENTICATED',right=self.left)
    def test_prefix_uncertain(self): self.check('PREFIX_UNCERTAIN',right=self.left+(T('WRITE','b',2,2,'w'),))
    def test_witness_for_left_fork_conflicts(self): self.check('WITNESS_CONFLICT',witnesses=(Witness('w1',3,self.b,True),))
    def test_witness_for_right_fork_conflicts(self): self.check('WITNESS_CONFLICT',witnesses=(Witness('w1',3,self.c,True),))
    def test_future_witness_unavailable(self): self.check('WITNESS_EVENT_UNAVAILABLE',witnesses=(Witness('w1',4,self.b,True),))
    def test_duplicate_identity(self): self.check('DUPLICATE_WITNESS_IDENTITY',witnesses=(Witness('w1',1,self.a,True),)*2)
    def test_unasserted_independence(self): self.check('INDEPENDENCE_NOT_ASSERTED',witnesses=(Witness('w1',1,self.a,False),))
    def test_invalid_witness(self): self.check('INVALID_WITNESS',witnesses=(Witness('w1',True,self.a,True),))
    def test_invalid_input(self): self.check('INVALID_INPUT',left=123)
    def test_invalid_local_history(self): self.check('INVALID_LOCAL_HISTORY',right=(self.a,self.c))
    def test_forged_agreement_not_authentication(self):
        forged=(self.a,self.r,T('ACQUIRE','attacker',2,1,'fake'))
        self.check('AGREED_FIXTURE_UNAUTHENTICATED',left=forged,right=forged)
    def test_witness_same_event_not_proof_of_independence(self):
        self.check('AGREED_FIXTURE_UNAUTHENTICATED',right=self.left,witnesses=(Witness('claimed-1',1,self.a,True),Witness('claimed-2',1,self.a,True)))

if __name__=='__main__': unittest.main()
