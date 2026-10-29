import unittest
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int50_concurrent_recovery_simulator import EpochEvidence as E
from tools.f3_int51_recovery_memory_simulator import RecoveryMemory
from tools.f3_int52_recovery_continuity_simulator import (
    ContinuityState as S, assess_continuity, safe_to_promote,
)


class ContinuityTests(unittest.TestCase):
    def args(self, epoch=5):
        chain=tuple(Membership(i,('a','b','c'),2,i-1) for i in range(2,epoch+1))
        return dict(history=chain,votes=tuple((('a','b'),('b','c')) for _ in range(len(chain)-1)),
                    reference=tuple(range(2,epoch+1)),returned=('a','b'),
                    evidence=(E('a',epoch,'pin'),E('b',epoch,'pin')),
                    copies=(chain,),pinned_digest='pin')

    def call(self,status,state=None,round_id='r1',**changes):
        if state is None: state=S()
        args=self.args()
        args.update(changes)
        result=assess_continuity(state,round_id,**args)
        self.assertEqual(result.status,status)
        self.assertEqual(result.f3,'OPEN')
        for field in ('orders_allowed','live_certified','flow_complete','f3_resolved',
                      'native_prototype_authorized','strict_deadline_guaranteed',
                      'authenticated_witness_verified'):
            self.assertIs(getattr(result,field),False)
        self.assertFalse(safe_to_promote(result))
        if status!='CONTINUITY_FIXTURE_UNAUTHENTICATED': self.assertIs(result.state,state)
        return result

    def seeded(self): return self.call('CONTINUITY_FIXTURE_UNAUTHENTICATED').state
    def test_bootstrap(self):
        state=S()
        result=self.call('CONTINUITY_FIXTURE_UNAUTHENTICATED',state=state)
        self.assertEqual(state,S())
        self.assertEqual(result.state.history,self.args()['history'])
    def test_extension(self):
        state=self.seeded()
        result=self.call('CONTINUITY_FIXTURE_UNAUTHENTICATED',state=state,round_id='r2',**self.args(6))
        self.assertEqual(result.state.history[:4],state.history)
    def test_membership_rewrite(self):
        state=self.seeded(); args=self.args(6)
        chain=(Membership(2,('a','b','d'),2,1),)+args['history'][1:]
        args.update(history=chain,copies=(chain,))
        self.call('REWRITTEN_MEMBERSHIP_PREFIX',state=state,round_id='r2',**args)
    def test_threshold_rewrite(self):
        state=self.seeded(); chain=(Membership(2,('a','b','c'),3,1),)+state.history[1:]
        self.call('REWRITTEN_MEMBERSHIP_PREFIX',state=state,history=chain)
    def test_predecessor_rewrite(self):
        state=self.seeded(); chain=(Membership(2,('a','b','c'),2,0),)+state.history[1:]
        self.call('REWRITTEN_MEMBERSHIP_PREFIX',state=state,history=chain)
    def test_vote_rewrite(self):
        state=self.seeded(); votes=((('a','c'),('b','c')),)+state.votes[1:]
        self.call('REWRITTEN_VOTE_PREFIX',state=state,votes=votes)
    def test_truncated_history(self):
        state=self.seeded(); self.call('TRUNCATED_PREFIX',state=state,history=state.history[:-1])
    def test_truncated_votes(self):
        state=self.seeded(); self.call('TRUNCATED_VOTE_PREFIX',state=state,votes=state.votes[:-1])
    def test_round_replay(self): self.call('REPLAYED_ROUND',state=self.seeded())
    def test_cross_round_replay(self): self.call('REPLAYED_CROSS_ROUND_EVIDENCE',state=self.seeded(),round_id='r2')
    def test_partition_unchanged(self): self.call('BASE_PARTITION_UNRESOLVED',partitioned=True)
    def test_new_bad_link(self):
        state=self.seeded(); args=self.args(6)
        chain=args['history'][:-1]+(Membership(6,('a','b','c'),2,4),)
        args.update(history=chain,copies=(chain,))
        self.call('BASE_BASE_BROKEN_EPOCH_LINK',state=state,round_id='r2',**args)
    def test_list_snapshot(self): self.call('INVALID_SNAPSHOT',history=list(self.args()['history']))
    def test_bad_history_member(self): self.call('INVALID_SNAPSHOT',history=('not-membership',))
    def test_missing_snapshot(self):
        state=S(); result=assess_continuity(state,'r1')
        self.assertEqual(result.status,'INVALID_SNAPSHOT'); self.assertIs(result.state,state)
    def test_bad_state(self): self.call('INVALID_CONTINUITY_STATE',state=S(history=[]))
    def test_orphan_memory(self): self.call('INCONSISTENT_CONTINUITY_STATE',state=S(RecoveryMemory(5,'pin',('r0',),(('a',5,'pin'),))))
    def test_memory_head_mismatch(self):
        state=self.seeded(); self.call('INCONSISTENT_CONTINUITY_STATE',state=S(state.memory,state.history[:-1],state.votes[:-1]))
    def test_small_bound(self): self.call('CONTINUITY_LIMIT_EXCEEDED',max_records=3)
    def test_bool_bound(self): self.call('INVALID_MEMORY_BOUND',max_records=False)
    def test_reject_then_extend(self):
        state=self.seeded()
        self.call('TRUNCATED_PREFIX',state=state,round_id='r2',history=state.history[:-1])
        self.call('CONTINUITY_FIXTURE_UNAUTHENTICATED',state=state,round_id='r2',**self.args(6))
    def test_multiple_extensions(self):
        state=S()
        for epoch in range(5,10):
            state=self.call('CONTINUITY_FIXTURE_UNAUTHENTICATED',state=state,round_id=str(epoch),**self.args(epoch)).state
        self.assertEqual((state.memory.epoch,len(state.history)),(9,8))
    def test_state_reset_stays_untrusted(self):
        self.seeded()
        result=self.call('CONTINUITY_FIXTURE_UNAUTHENTICATED',state=S())
        self.assertFalse(result.authenticated_witness_verified)


if __name__=='__main__': unittest.main()
