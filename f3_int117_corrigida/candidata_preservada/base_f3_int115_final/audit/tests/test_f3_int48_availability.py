import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int48_availability_simulator import assess_availability,safe_to_promote

class AvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.chain=tuple(Membership(i,('a','b','c'),2,i-1) for i in range(2,6))
        self.votes=tuple((('a','b'),('b','c')) for _ in range(3))
    def check(self,status,**changes):
        args=dict(chain=self.chain,votes=self.votes,reference=(2,3,4,5),copies=(self.chain,),max_steps=64)
        args.update(changes)
        r=assess_availability(**args)
        self.assertEqual(r.status,status)
        for field in ('authenticated','authoritative','closure_authorized','consensus_verified','native_fencing_verified','orders_allowed'):
            self.assertFalse(getattr(r,field))
        self.assertFalse(safe_to_promote(r))
    def test_consistent_fixture(self): self.check('AVAILABLE_FIXTURE_UNAUTHENTICATED')
    def test_missing_reference(self): self.check('MISSING_OR_INVALID_REFERENCE',reference=None)
    def test_reference_mismatch(self): self.check('REFERENCE_MISMATCH',reference=(2,3,4,6))
    def test_missing_votes(self): self.check('INCOMPLETE_VOTES',votes=self.votes[:2])
    def test_missing_copies(self): self.check('MISSING_INDEPENDENT_COPIES',copies=())
    def test_truncated_copy(self): self.check('DIVERGENT_OR_TRUNCATED_COPY',copies=(self.chain[:-1],))
    def test_divergent_copy(self): self.check('DIVERGENT_OR_TRUNCATED_COPY',copies=(self.chain[:-1]+(Membership(5,('a','b','d'),2,4),),))
    def test_partition(self): self.check('PARTITION_AVAILABILITY_UNCERTAIN',partitioned=True)
    def test_quorum_unavailable(self): self.check('QUORUM_UNAVAILABLE',unavailable=('a','b'))
    def test_one_unavailable(self): self.check('AVAILABLE_FIXTURE_UNAUTHENTICATED',unavailable=('a',))
    def test_unknown_unavailable(self): self.check('UNKNOWN_UNAVAILABLE_WITNESS',unavailable=('x',))
    def test_misleading_quorum(self): self.check('MISLEADING_QUORUM_CLAIM',claimed_quorum=3)
    def test_invalid_claim(self): self.check('INVALID_QUORUM_CLAIM',claimed_quorum=True)
    def test_bound(self): self.check('INVALID_BOUNDS',max_steps=3)
    def test_invalid_copy(self): self.check('INVALID_COPY',copies=(None,))
    def test_invalid_history(self): self.check('INVALID_HISTORY',chain=())
    def test_long_history_bounded(self):
        c=tuple(Membership(i,('a','b','c'),2,i-1) for i in range(2,42))
        v=tuple((('a','b'),('b','c')) for _ in range(39))
        self.check('AVAILABLE_FIXTURE_UNAUTHENTICATED',chain=c,votes=v,reference=tuple(range(2,42)),copies=(c,))
    def test_long_history_rejected_at_bound(self):
        c=tuple(Membership(i,('a','b','c'),2,i-1) for i in range(2,42))
        self.check('INVALID_BOUNDS',chain=c,max_steps=32)

if __name__=='__main__': unittest.main()
