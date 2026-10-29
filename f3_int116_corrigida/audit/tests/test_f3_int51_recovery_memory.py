import itertools
import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int50_concurrent_recovery_simulator import EpochEvidence as E
from tools.f3_int51_recovery_memory_simulator import (
    RecoveryMemory as M, assess_round, safe_to_promote,
)

LOCKS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')


class MemoryTests(unittest.TestCase):
    def args(self, epoch=5, digest='pin'):
        chain = tuple(Membership(i, ('a','b','c'), 2, i-1) for i in range(2,epoch+1))
        return dict(history=chain, votes=tuple((('a','b'),('b','c')) for _ in range(len(chain)-1)),
                    reference=tuple(range(2,epoch+1)), returned=('a','b'),
                    evidence=(E('a',epoch,digest),E('b',epoch,digest)),
                    copies=(chain,), pinned_digest=digest)

    def call(self, status, memory=None, round_id='r1', **changes):
        if memory is None: memory=M()
        args = self.args()
        args.update(changes)
        result=assess_round(memory, round_id, **args)
        self.assertEqual(result.status,status)
        self.assertEqual(result.f3,'OPEN')
        for lock in LOCKS: self.assertIs(getattr(result,lock),False)
        self.assertFalse(safe_to_promote(result))
        if status != 'RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED':
            self.assertIs(result.memory,memory)
        return result

    def seeded(self): return self.call('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED').memory
    def test_initial(self):
        before=M()
        after=self.call('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED',memory=before).memory
        self.assertEqual(before,M())
        self.assertEqual((after.epoch,after.rounds,len(after.consumed)),(5,('r1',),2))
    def test_round_replay(self): self.call('REPLAYED_ROUND',memory=self.seeded())
    def test_evidence_replay(self): self.call('REPLAYED_CROSS_ROUND_EVIDENCE',memory=self.seeded(),round_id='r2')
    def test_evidence_reordered_replay(self): self.call('REPLAYED_CROSS_ROUND_EVIDENCE',memory=self.seeded(),round_id='r2',evidence=self.args()['evidence'][::-1])
    def test_advance(self):
        memory=self.seeded()
        result=self.call('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED',memory=memory,round_id='r2',**self.args(6,'new'))
        self.assertEqual(result.memory.epoch,6)
        self.assertEqual(memory.epoch,5)
    def test_rollback(self):
        memory=self.call('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED',**self.args(6)).memory
        self.call('EPOCH_ROLLBACK',memory=memory,round_id='r2')
    def test_digest_conflict(self): self.call('PIN_CONFLICT_WITH_MEMORY',memory=self.seeded(),round_id='r2',pinned_digest='evil')
    def test_failed_attempt_does_not_consume(self):
        memory=M()
        self.call('BASE_PARTITION_UNRESOLVED',memory=memory,partitioned=True)
        self.call('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED',memory=memory)
    def test_atomic_memory_capacity(self): self.call('MEMORY_LIMIT_EXCEEDED',memory=self.seeded(),round_id='r2',max_records=3,**self.args(6))
    def test_bound(self): self.call('INVALID_MEMORY_BOUND',max_records=True)
    def test_bad_memory(self): self.call('INVALID_MEMORY',memory=M(True,'x'))
    def test_missing_consumption(self): self.call('INVALID_MEMORY',memory=M(5,'pin',('r0',),()))
    def test_unhashable_token(self): self.call('INVALID_MEMORY',memory=M(5,'pin',('r0',),(([],5,'pin'),)))
    def test_duplicate_token(self): self.call('INVALID_MEMORY',memory=M(5,'pin',('r0',),(('a',5,'pin'),)*2))
    def test_future_memory_token(self): self.call('INVALID_MEMORY',memory=M(5,'pin',('r0',),(('a',6,'pin'),)))
    def test_inconsistent_memory_digest(self): self.call('INVALID_MEMORY',memory=M(5,'pin',('r0',),(('a',5,'other'),)))
    def test_empty_round_id(self): self.call('INVALID_ROUND_ID',round_id='')
    def test_bad_reference(self): self.call('INVALID_REFERENCE',reference=None)
    def test_unknown_argument(self): self.call('INVALID_RECOVERY_ARGUMENTS',unknown=True)
    def test_noniterable_evidence(self): self.call('INVALID_EVIDENCE',evidence=None)
    def test_missing_arguments(self):
        memory=M()
        result=assess_round(memory,'r1')
        self.assertEqual(result.status,'INVALID_RECOVERY_ARGUMENTS')
        self.assertIs(result.memory,memory)
    def test_infinite_evidence(self): self.call('MEMORY_LIMIT_EXCEEDED',evidence=itertools.repeat(E('a',5,'pin')))
    def test_rejected_equivocation(self): self.call('BASE_EQUIVOCATION',evidence=(E('a',5,'pin'),E('a',5,'bad')))
    def test_long_sequence(self):
        memory=M()
        for epoch in range(5,12):
            memory=self.call('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED',memory=memory,
                             round_id=str(epoch),**self.args(epoch,str(epoch))).memory
        self.assertEqual((memory.epoch,len(memory.rounds),len(memory.consumed)),(11,7,14))
    def test_caller_replacement_is_untrusted(self):
        self.seeded()
        result=self.call('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED',memory=M())
        self.assertFalse(result.authenticated_witness_verified)


if __name__ == '__main__': unittest.main()
