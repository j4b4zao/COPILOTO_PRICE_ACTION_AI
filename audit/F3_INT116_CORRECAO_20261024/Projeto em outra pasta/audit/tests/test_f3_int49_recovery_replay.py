import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int49_recovery_replay_simulator import assess_recovery,safe_to_promote

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.chain=tuple(Membership(i,('a','b','c'),2,i-1) for i in range(2,6))
        self.votes=tuple((('a','b'),('b','c')) for _ in range(3))
    def check(self,status,**changes):
        kwargs=dict(history=self.chain,votes=self.votes,reference=(2,3,4,5),
                    returned=('a','b'),offline=('c',),recovery_evidence=(('a',5),('b',5)),
                    copies=(self.chain,))
        kwargs.update(changes)
        result=assess_recovery(**kwargs)
        self.assertEqual(result.status,status)
        for name in ('authenticated','authoritative','closure_authorized','consensus_verified',
                     'native_fencing_verified','orders_allowed'):
            self.assertFalse(getattr(result,name))
        self.assertFalse(safe_to_promote(result))
    def test_return_consistent_untrusted(self): self.check('RECOVERY_FIXTURE_UNAUTHENTICATED')
    def test_missing_reference(self): self.check('MISSING_OR_INVALID_REFERENCE',reference=None)
    def test_reference_mismatch(self): self.check('REFERENCE_MISMATCH',reference=(2,3,4,6))
    def test_incomplete_votes(self): self.check('INCOMPLETE_VOTES',votes=self.votes[:1])
    def test_no_return(self): self.check('NO_RETURNED_WITNESS',returned=(),recovery_evidence=())
    def test_duplicate_witness(self): self.check('DUPLICATE_WITNESS',returned=('a','a'))
    def test_contradictory_availability(self): self.check('CONTRADICTORY_AVAILABILITY',offline=('a',))
    def test_unknown_witness(self): self.check('UNKNOWN_WITNESS',returned=('x',))
    def test_replayed_evidence(self): self.check('REPLAYED_WITNESS_EVIDENCE',recovery_evidence=(('a',5),('a',5)))
    def test_stale_evidence(self): self.check('STALE_REPLAYED_EVIDENCE',recovery_evidence=(('a',4),('b',5)))
    def test_future_evidence(self): self.check('FUTURE_UNPINNED_EVIDENCE',recovery_evidence=(('a',6),('b',5)))
    def test_missing_evidence(self): self.check('MISSING_OR_EXTRA_EVIDENCE',recovery_evidence=(('a',5),))
    def test_quorum_unavailable(self): self.check('QUORUM_STILL_UNAVAILABLE',returned=('a',),offline=('b','c'),recovery_evidence=(('a',5),))
    def test_missing_copies(self): self.check('MISSING_COPIES',copies=())
    def test_truncated_copy(self): self.check('DIVERGENT_OR_TRUNCATED_COPY',copies=(self.chain[:-1],))
    def test_partition_unresolved(self): self.check('PARTITION_UNRESOLVED',partitioned=True)
    def test_invalid_evidence(self): self.check('INVALID_RECOVERY_EVIDENCE',recovery_evidence=('a',))
    def test_bound(self): self.check('INVALID_BOUNDS',max_steps=3)

if __name__=='__main__': unittest.main()
