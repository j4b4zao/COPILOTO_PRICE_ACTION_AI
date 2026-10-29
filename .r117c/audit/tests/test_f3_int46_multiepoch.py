import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int46_multiepoch_simulator import audit_epochs, safe_to_promote

class MultiEpochTests(unittest.TestCase):
    def setUp(self):
        self.chain = tuple(Membership(i,('a','b','c'),2,i-1) for i in (2,3,4))
        self.votes = ((('a','b'),('b','c')), (('a','b'),('b','c')))
    def check(self, expected, **kwargs):
        args = dict(memberships=self.chain, vote_pairs=self.votes, pinned_epochs=(2,3,4))
        args.update(kwargs)
        result = audit_epochs(**args)
        self.assertEqual(result.status,expected)
        self.assertFalse(result.authenticated or result.authoritative or result.closure_authorized or result.consensus_verified)
        self.assertFalse(safe_to_promote(result))
    def test_valid_fixture_not_authenticated(self): self.check('CHAIN_FIXTURE_UNAUTHENTICATED')
    def test_missing_pin(self): self.check('UNPINNED_HISTORY',pinned_epochs=None)
    def test_pin_mismatch(self): self.check('PIN_MISMATCH',pinned_epochs=(2,3,5))
    def test_invalid_pin(self): self.check('INVALID_PIN',pinned_epochs=(2,True,4))
    def test_replayed_epoch(self): self.check('ROLLBACK_OR_REPLAY',memberships=(self.chain[0],self.chain[1],self.chain[0]),pinned_epochs=(2,3,2))
    def test_backward_epoch(self): self.check('ROLLBACK_OR_REPLAY',memberships=(self.chain[1],self.chain[0]),vote_pairs=self.votes[:1],pinned_epochs=(3,2))
    def test_skipped_epoch(self): self.check('BROKEN_EPOCH_LINK',memberships=(self.chain[0],self.chain[2]),vote_pairs=self.votes[:1],pinned_epochs=(2,4))
    def test_wrong_predecessor(self): self.check('BROKEN_EPOCH_LINK',memberships=(self.chain[0],Membership(3,('a','b','c'),2,0)),vote_pairs=self.votes[:1],pinned_epochs=(2,3))
    def test_partition(self): self.check('PARTITION_CONTESTED_UNAUTHENTICATED',partitioned=True)
    def test_compromised(self): self.check('COMPROMISED_VOTER',compromised=('b',))
    def test_collusion(self): self.check('SUSPECTED_COLLUSION',suspected_collusion=(('a','b'),))
    def test_vote_pair_missing(self): self.check('INVALID_LENGTH',vote_pairs=self.votes[:1])
    def test_disjoint_quorum(self): self.check('QUORUM_INTERSECTION_NOT_GUARANTEED',memberships=(self.chain[0],Membership(3,('b','c','d'),2,2)),vote_pairs=self.votes[:1],pinned_epochs=(2,3))
    def test_weak_votes(self): self.check('INSUFFICIENT_JOINT_VOTES',vote_pairs=((('a',),('b','c')),self.votes[1]))
    def test_invalid_input(self): self.check('INVALID_INPUT',memberships=None)
    def test_single_epoch(self): self.check('INVALID_LENGTH',memberships=self.chain[:1],vote_pairs=(),pinned_epochs=(2,))

if __name__ == '__main__': unittest.main()
