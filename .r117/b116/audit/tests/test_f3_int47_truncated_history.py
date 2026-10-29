import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int47_truncated_history_simulator import assess_evidence,safe_to_promote

class TruncatedHistoryTests(unittest.TestCase):
    def setUp(self):
        self.chain=tuple(Membership(i,('a','b','c'),2,i-1) for i in (2,3,4))
        self.votes=((('a','b'),('b','c')),(('a','b'),('b','c')))
    def check(self,status,**overrides):
        args=dict(left=self.chain,right=self.chain,left_votes=self.votes,right_votes=self.votes,pinned_epochs=(2,3,4),anchor=(2,3,4))
        args.update(overrides)
        r=assess_evidence(**args)
        self.assertEqual(r.status,status)
        self.assertFalse(r.authenticated or r.authoritative or r.closure_authorized or r.consensus_verified or r.native_fencing_verified)
        self.assertFalse(safe_to_promote(r))
    def test_consistent_fixture(self): self.check('EVIDENCE_FIXTURE_UNAUTHENTICATED')
    def test_missing_anchor(self): self.check('MISSING_EXTERNAL_REFERENCE',anchor=None)
    def test_missing_pin(self): self.check('MISSING_EXTERNAL_REFERENCE',pinned_epochs=None)
    def test_invalid_reference(self): self.check('INVALID_REFERENCE',anchor=(2,True,4))
    def test_anchor_mismatch(self): self.check('ANCHOR_PIN_CONFLICT',anchor=(2,3,5))
    def test_left_truncated(self): self.check('TRUNCATED_HISTORY',left=self.chain[:2],left_votes=self.votes[:1])
    def test_right_truncated(self): self.check('TRUNCATED_HISTORY',right=self.chain[:2],right_votes=self.votes[:1])
    def test_rewritten_epoch(self): self.check('HISTORY_PIN_CONFLICT',right=(self.chain[0],Membership(7,('a','b','c'),2,2),self.chain[2]))
    def test_membership_fork(self): self.check('DIVERGENT_MEMBERSHIP',right=(self.chain[0],Membership(3,('a','b','d'),2,2),self.chain[2]))
    def test_coordinated_vote_rewrite(self): self.check('COORDINATED_VOTE_CONFLICT',right_votes=((('a','c'),('b','c')),self.votes[1]))
    def test_partition(self): self.check('PARTITION_CONTESTED_UNAUTHENTICATED',partitioned=True)
    def test_compromised(self): self.check('COMPROMISED_VOTER',compromised=('b',))
    def test_collusion(self): self.check('SUSPECTED_COLLUSION',suspected_collusion=(('a','b'),))
    def test_nonadjacent_gap(self):
        c=(Membership(2,('a','b','c'),2,1),Membership(3,('a','b','c','d','e'),4,2),Membership(4,('c','d','e'),2,3))
        v=((('a','b'),('a','b','c','d')),(('a','b','c','d'),('c','d')))
        self.check('NONADJACENT_QUORUM_GAP',left=c,right=c,left_votes=v,right_votes=v)
    def test_bad_input(self): self.check('INVALID_INPUT',left=None)
    def test_bad_bound(self): self.check('INVALID_BOUNDS',max_steps=2)
    def test_malformed_vote(self): self.check('INVALID_LENGTH',left_votes=self.votes[:1],right_votes=self.votes[:1])
    def test_single_epoch(self): self.check('INVALID_LENGTH',left=self.chain[:1],right=self.chain[:1],left_votes=(),right_votes=(),pinned_epochs=(2,),anchor=(2,))

if __name__=='__main__': unittest.main()
