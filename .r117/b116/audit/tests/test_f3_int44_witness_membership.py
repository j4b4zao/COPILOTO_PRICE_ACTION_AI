import unittest
from tools.f3_int41_worker_handoff_simulator import Transfer
from tools.f3_int43_partition_reconciliation_simulator import Witness
from tools.f3_int44_witness_membership_simulator import Membership, assess_membership, safe_to_promote

class MembershipTests(unittest.TestCase):
    def setUp(self):
        self.event=Transfer('ACQUIRE','a',1,0,'a1')
        self.history=(self.event,)
        self.w=(Witness('w1',1,self.event,True),Witness('w2',1,self.event,True))
        self.m=Membership(2,('w1','w2','w3'),2,1)
    def check(self, expected, **kw):
        args=dict(left=self.history,right=self.history,witnesses=self.w,membership=self.m,pinned_epoch=2)
        args.update(kw)
        result=assess_membership(**args)
        self.assertEqual(result.status,expected)
        self.assertFalse(result.authenticated or result.authoritative or result.closure_authorized or result.independent_verified)
        self.assertFalse(safe_to_promote(result))
    def test_unverified_quorum(self): self.check('QUORUM_FIXTURE_UNAUTHENTICATED')
    def test_missing_pin(self): self.check('UNPINNED_MEMBERSHIP',pinned_epoch=None)
    def test_stale_membership(self): self.check('MEMBERSHIP_EPOCH_MISMATCH',pinned_epoch=3)
    def test_invalid_pin(self): self.check('INVALID_PIN',pinned_epoch=True)
    def test_duplicate_membership(self): self.check('INVALID_MEMBERSHIP',membership=Membership(2,('w1','w1'),1,1))
    def test_invalid_threshold(self): self.check('INVALID_MEMBERSHIP',membership=Membership(2,('w1',),2,1))
    def test_invalid_predecessor(self): self.check('INVALID_MEMBERSHIP',membership=Membership(2,('w1','w2'),1,2))
    def test_nonmember(self): self.check('NON_MEMBER_WITNESS',witnesses=(Witness('intruder',1,self.event,True),))
    def test_compromised(self): self.check('COMPROMISED_WITNESS',compromised=('w2',))
    def test_collusion(self): self.check('SUSPECTED_COLLUSION',suspected_collusion=(('w1','w2'),))
    def test_insufficient_votes(self): self.check('INSUFFICIENT_FIXTURE_VOTES',witnesses=self.w[:1])
    def test_duplicate_votes(self): self.check('DUPLICATE_WITNESS_IDENTITY',witnesses=self.w[:1]*2)
    def test_conflicting_history(self): self.check('BASE_NO_WITNESS',witnesses=()) if False else self.check('BASE_WITNESS_CONFLICT',right=(Transfer('ACQUIRE','b',1,0,'b1'),))
    def test_unasserted_independence(self): self.check('BASE_INDEPENDENCE_NOT_ASSERTED',witnesses=(Witness('w1',1,self.event,False),Witness('w2',1,self.event,True)))
    def test_forged_colluding_identifiers(self): self.check('QUORUM_FIXTURE_UNAUTHENTICATED',witnesses=(Witness('w1',1,self.event,True),Witness('w2',1,self.event,True)))
    def test_invalid_witness_type(self): self.check('INVALID_WITNESS',witnesses=('w1','w2'))

if __name__=='__main__': unittest.main()
