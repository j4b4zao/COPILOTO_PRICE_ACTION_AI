import unittest
from dataclasses import replace
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int50_concurrent_recovery_simulator import EpochEvidence as E
from tools.f3_int53_interleaving_simulator import Snapshot, Proposal, prepare, commit, safe_to_promote


def recovery(epoch=5, pin='pin'):
    chain = tuple(Membership(i, ('a','b','c'), 2, i-1) for i in range(2, epoch+1))
    return dict(history=chain, votes=tuple((('a','b'),('b','c')) for _ in chain[1:]),
                reference=tuple(range(2, epoch+1)), returned=('a','b'),
                evidence=(E('a',epoch,pin), E('b',epoch,pin)), copies=(chain,), pinned_digest=pin)


class InterleavingTests(unittest.TestCase):
    def proposal(self, snapshot=None, round_id='r1', **changes):
        args = recovery(); args.update(changes)
        return prepare(snapshot or Snapshot(), round_id, **args)

    def test_prepare_no_mutation(self):
        s=Snapshot(); p=self.proposal(s); self.assertEqual(s, Snapshot()); self.assertEqual(p.snapshot,s)
    def test_commit_advances(self):
        s=Snapshot(); r=commit(s,self.proposal(s).proposal)
        self.assertEqual((r.snapshot.version,r.snapshot.state.memory.epoch),(1,5))
    def test_competing_rounds_first_wins(self):
        s=Snapshot(); a=self.proposal(s).proposal; b=self.proposal(s,'r2').proposal
        current=commit(s,a).snapshot
        self.assertEqual(commit(current,b).status,'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_reverse_winner(self):
        s=Snapshot(); a=self.proposal(s).proposal; b=self.proposal(s,'r2').proposal
        current=commit(s,b).snapshot
        self.assertEqual(current.state.memory.rounds,('r2',))
        self.assertIs(commit(current,a).snapshot,current)
    def test_duplicate_commit(self):
        s=Snapshot(); p=self.proposal(s).proposal; current=commit(s,p).snapshot
        self.assertEqual(commit(current,p).status,'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_version_only_conflict(self):
        p=self.proposal().proposal
        self.assertEqual(commit(Snapshot(1),p).status,'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_state_only_conflict(self):
        p=self.proposal().proposal; s=Snapshot(0,p.candidate)
        self.assertEqual(commit(s,p).status,'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_forged_candidate(self):
        p=self.proposal().proposal
        self.assertEqual(commit(Snapshot(),replace(p,candidate=Snapshot().state)).status,'FORGED_CANDIDATE')
    def test_forged_round(self):
        p=self.proposal().proposal
        self.assertEqual(commit(Snapshot(),replace(p,round_id='other')).status,'FORGED_CANDIDATE')
    def test_duplicate_argument(self):
        p=self.proposal().proposal
        self.assertEqual(commit(Snapshot(),replace(p,arguments=p.arguments+(p.arguments[0],))).status,'INVALID_PROPOSAL')
    def test_bad_argument_shape(self):
        p=self.proposal().proposal
        self.assertEqual(commit(Snapshot(),replace(p,arguments=('bad',))).status,'INVALID_PROPOSAL')
    def test_mutable_history_rejected(self):
        self.assertEqual(self.proposal(history=list(recovery()['history'])).status,'INVALID_IMMUTABLE_ARGUMENTS')
    def test_partition_rejected(self):
        self.assertIsNone(self.proposal(partitioned=True).proposal)
    def test_bad_version_bool(self):
        self.assertEqual(self.proposal(Snapshot(True)).status,'INVALID_SHARED_SNAPSHOT')
    def test_bad_version_negative(self):
        self.assertEqual(self.proposal(Snapshot(-1)).status,'INVALID_SHARED_SNAPSHOT')
    def test_invalid_proposal(self):
        self.assertEqual(commit(Snapshot(),None).status,'INVALID_PROPOSAL')
    def test_invalid_commit_snapshot(self):
        self.assertEqual(commit(None,None).status,'INVALID_SHARED_SNAPSHOT')
    def test_rebase_extension(self):
        s=commit(Snapshot(),self.proposal().proposal).snapshot
        p=prepare(s,'r2',**recovery(6)).proposal
        self.assertEqual(commit(s,p).snapshot.state.memory.rounds,('r1','r2'))
    def test_rebase_replay(self):
        s=commit(Snapshot(),self.proposal().proposal).snapshot
        self.assertEqual(self.proposal(s).status,'REPLAYED_ROUND')
    def test_branch_conflict(self):
        a=self.proposal().proposal; b=self.proposal(pinned_digest='other',evidence=(E('a',5,'other'),E('b',5,'other'))).proposal
        self.assertEqual(commit(commit(Snapshot(),a).snapshot,b).status,'STALE_OR_CONFLICTING_SNAPSHOT')
    def test_rejection_atomic(self):
        s=Snapshot(); r=commit(s,None); self.assertIs(r.snapshot,s); self.assertEqual(s,Snapshot())
    def test_flags(self):
        for r in (self.proposal(),commit(Snapshot(),self.proposal().proposal),commit(Snapshot(),None)):
            self.assertEqual(r.f3,'OPEN')
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
            self.assertFalse(safe_to_promote(r))
