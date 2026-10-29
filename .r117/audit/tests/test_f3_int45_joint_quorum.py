import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int45_joint_quorum_simulator import assess_joint, safe_to_promote

class JointQuorumTests(unittest.TestCase):
    def setUp(self):
        self.old = Membership(2, ('a','b','c'), 2, 1)
        self.new = Membership(3, ('b','c','d'), 2, 2)
        self.args = dict(old=self.old, new=self.new, left_votes=('a','b'),
                         right_votes=('b','d'), pinned_epochs=(2,3))
    def check(self, status, **updates):
        args = dict(self.args); args.update(updates)
        r = assess_joint(**args)
        self.assertEqual(r.status, status)
        self.assertFalse(r.authenticated or r.authoritative or r.closure_authorized or r.consensus_verified)
        self.assertFalse(safe_to_promote(r))
    def test_weak_overlap_not_guaranteed(self): self.check('QUORUM_INTERSECTION_NOT_GUARANTEED')
    def test_missing_pin(self): self.check('UNPINNED_TRANSITION', pinned_epochs=None)
    def test_wrong_pin(self): self.check('PIN_MISMATCH', pinned_epochs=(2,4))
    def test_invalid_pin(self): self.check('INVALID_PIN', pinned_epochs=(True,3))
    def test_broken_transition(self): self.check('BROKEN_TRANSITION', new=Membership(4,('b','c','d'),2,1),pinned_epochs=(2,4))
    def test_duplicate_vote(self): self.check('INVALID_VOTES',left_votes=('a','a'))
    def test_nonmember(self): self.check('NON_MEMBER_VOTE',right_votes=('x','d'))
    def test_compromised(self): self.check('COMPROMISED_VOTER',compromised=('b',))
    def test_collusion(self): self.check('SUSPECTED_COLLUSION',suspected_collusion=(('a','b'),))
    def test_insufficient(self): self.check('INSUFFICIENT_JOINT_VOTES',left_votes=('a',))
    def test_disjoint_membership(self): self.check('DISJOINT_MEMBERSHIP',new=Membership(3,('d','e','f'),2,2),right_votes=('d','e'))
    def test_strong_joint_fixture(self):
        strong = Membership(3,('a','b','c'),2,2)
        self.check('JOINT_FIXTURE_UNAUTHENTICATED',new=strong,right_votes=('b','c'))
    def test_partition_contested(self):
        strong = Membership(3,('a','b','c'),2,2)
        self.check('PARTITION_CONTESTED_UNAUTHENTICATED',new=strong,right_votes=('b','c'),partitioned=True)
    def test_invalid_membership(self): self.check('INVALID_MEMBERSHIP',new=Membership(3,('b','b'),1,2))

if __name__ == '__main__': unittest.main()
