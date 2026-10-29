import itertools
import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int50_concurrent_recovery_simulator import (
    EpochEvidence as E, assess_concurrent, safe_to_promote,
)

LOCKS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')


class ConcurrentTests(unittest.TestCase):
    def setUp(self):
        self.chain = tuple(Membership(i, ('a', 'b', 'c'), 2, i-1) for i in range(2, 6))
        self.args = dict(history=self.chain,
                         votes=tuple((('a', 'b'), ('b', 'c')) for _ in range(3)),
                         reference=(2, 3, 4, 5), returned=('a', 'b'), offline=('c',),
                         evidence=(E('a', 5, 'pin'), E('b', 5, 'pin')),
                         copies=(self.chain,), pinned_digest='pin')

    def check(self, expected, **changes):
        args = dict(self.args, **changes)
        result = assess_concurrent(**args)
        self.assertEqual(result.status, expected)
        self.assertEqual(result.f3, 'OPEN')
        for name in LOCKS:
            self.assertIs(getattr(result, name), False)
        self.assertFalse(safe_to_promote(result))
        return result

    def test_consistent(self):
        self.assertEqual(self.check('CONCURRENT_RECOVERY_FIXTURE_UNAUTHENTICATED').checked, 2)
    def test_reordered(self): self.check('CONCURRENT_RECOVERY_FIXTURE_UNAUTHENTICATED', evidence=self.args['evidence'][::-1])
    def test_replay(self): self.check('REPLAYED_EVIDENCE', evidence=(E('a',5,'pin'),)*2)
    def test_equivocation(self): self.check('EQUIVOCATION', evidence=(E('a',5,'pin'),E('a',5,'other')))
    def test_future(self): self.check('FUTURE_COMPETING_EPOCH', evidence=(E('a',6,'pin'),E('b',5,'pin')))
    def test_stale(self): self.check('STALE_COMPETING_EPOCH', evidence=(E('a',4,'pin'),E('b',5,'pin')))
    def test_digest(self): self.check('DIVERGENT_DIGEST', evidence=(E('a',5,'bad'),E('b',5,'pin')))
    def test_pin_missing(self): self.check('MISSING_DIGEST_PIN', pinned_digest=None)
    def test_unknown(self): self.check('BASE_MISSING_OR_EXTRA_EVIDENCE', evidence=(E('x',5,'pin'),))
    def test_empty(self): self.check('BASE_MISSING_OR_EXTRA_EVIDENCE', evidence=())
    def test_partition(self): self.check('BASE_PARTITION_UNRESOLVED', partitioned=True)
    def test_partition_flag(self): self.check('INVALID_PARTITION_FLAG', partitioned='false')
    def test_copy(self): self.check('BASE_DIVERGENT_OR_TRUNCATED_COPY', copies=(self.chain[:-1],))
    def test_missing_votes(self): self.check('BASE_INCOMPLETE_VOTES', votes=())
    def test_no_quorum(self): self.check('BASE_QUORUM_STILL_UNAVAILABLE', returned=('a',), offline=('b','c'), evidence=(E('a',5,'pin'),))
    def test_bad_evidence(self): self.check('INVALID_EVIDENCE', evidence=(('a',5,'pin'),))
    def test_bool_epoch(self): self.check('INVALID_EVIDENCE', evidence=(E('a',True,'pin'),))
    def test_bad_reference(self): self.check('INVALID_REFERENCE', reference=(2,3,3,5))
    def test_bool_bound(self): self.check('INVALID_BOUNDS', max_steps=True)
    def test_large_bound(self): self.check('INVALID_BOUNDS', max_steps=4097)
    def test_infinite_evidence(self): self.check('INPUT_LIMIT_EXCEEDED', evidence=itertools.repeat(E('a',5,'pin')))
    def test_noniterable(self): self.check('INVALID_INPUT', evidence=None)
    def test_infinite_history(self): self.check('INPUT_LIMIT_EXCEEDED', history=itertools.repeat(self.chain[0]))
    def test_malformed_membership(self): self.check('INVALID_MEMBERSHIP', history=(Membership(2,None,2),))
    def test_malformed_votes(self): self.check('INVALID_VOTES', votes=((('a',), ([],)),))
    def test_all_permutations_conflict(self):
        for evidence in itertools.permutations((E('a',5,'pin'),E('a',5,'bad'),E('b',5,'pin'))):
            self.check('EQUIVOCATION', evidence=evidence)


if __name__ == '__main__': unittest.main()
