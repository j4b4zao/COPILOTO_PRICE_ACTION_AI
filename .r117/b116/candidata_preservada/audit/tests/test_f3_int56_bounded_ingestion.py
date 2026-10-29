import unittest
from dataclasses import replace
from test_f3_int53_interleaving import recovery
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int56_bounded_ingestion_simulator import bounded_prepare, bounded_commit, scan, InputRejected, safe_to_promote


class IngestionTests(unittest.TestCase):
    def prepare(self,**changes):
        args=recovery(); args.update(changes)
        return bounded_prepare(Snapshot(),'r1',**args)
    def test_valid_prepare_commit(self):
        p=self.prepare().proposal
        self.assertEqual(bounded_commit(Snapshot(),p).snapshot.version,1)
    def test_deep_tuple(self):
        value=()
        for _ in range(40): value=(value,)
        self.assertEqual(self.prepare(votes=value).status,'INPUT_DEPTH_LIMIT')
    def test_recursive_list(self):
        value=[]; value.append(value)
        self.assertEqual(self.prepare(votes=value).status,'MUTABLE_OR_UNKNOWN_INPUT')
    def test_nested_list_membership(self):
        chain=(Membership(2,['a','b'],2,1),)
        self.assertEqual(self.prepare(history=chain).status,'MUTABLE_OR_UNKNOWN_INPUT')
    def test_generator_not_consumed(self):
        calls=[]
        def gen(): calls.append(1); yield 2
        self.assertEqual(self.prepare(reference=gen()).status,'MUTABLE_OR_UNKNOWN_INPUT'); self.assertEqual(calls,[])
    def test_unknown_object_not_inspected(self):
        class Hostile:
            def __iter__(self): raise AssertionError('called')
        self.assertEqual(self.prepare(votes=Hostile()).status,'MUTABLE_OR_UNKNOWN_INPUT')
    def test_node_bound(self):
        self.assertEqual(self.prepare(bounds={'max_nodes':8}).status,'INPUT_NODE_LIMIT')
    def test_string_bound(self):
        self.assertEqual(self.prepare(pinned_digest='x'*4097).status,'INPUT_STRING_LIMIT')
    def test_invalid_bool_bound(self):
        self.assertEqual(self.prepare(bounds={'max_depth':True}).status,'INVALID_INGESTION_BOUND')
    def test_invalid_zero_bound(self):
        self.assertEqual(self.prepare(bounds={'max_nodes':0}).status,'INVALID_INGESTION_BOUND')
    def test_invalid_large_depth(self):
        self.assertEqual(self.prepare(bounds={'max_depth':33}).status,'INVALID_INGESTION_BOUND')
    def test_unknown_bound(self):
        self.assertEqual(self.prepare(bounds={'unknown':3}).status,'INVALID_INGESTION_BOUND')
    def test_invalid_bounds_container(self):
        self.assertEqual(self.prepare(bounds=[]).status,'INVALID_INGESTION_BOUND')
    def test_exact_node_bound(self):
        scan(('a',),max_nodes=2)
        with self.assertRaisesRegex(InputRejected,'INPUT_NODE_LIMIT'): scan(('a',),max_nodes=1)
    def test_exact_depth_bound(self):
        scan(('a',),max_depth=1)
        with self.assertRaisesRegex(InputRejected,'INPUT_DEPTH_LIMIT'): scan((('a',),),max_depth=1)
    def test_exact_string_bound(self):
        scan('abc',max_string=3)
        with self.assertRaisesRegex(InputRejected,'INPUT_STRING_LIMIT'): scan('abcd',max_string=3)
    def test_mutable_proposal(self):
        p=self.prepare().proposal
        self.assertEqual(bounded_commit(Snapshot(),replace(p,arguments=[])).status,'MUTABLE_OR_UNKNOWN_INPUT')
    def test_commit_bound_atomic(self):
        p=self.prepare().proposal; s=Snapshot(); r=bounded_commit(s,p,bounds={'max_nodes':2})
        self.assertEqual(r.status,'INPUT_NODE_LIMIT'); self.assertIs(r.snapshot,s)
    def test_snapshot_nested_mutation(self):
        s=Snapshot(); bad=replace(s,state=replace(s.state,history=[]))
        self.assertEqual(bounded_prepare(bad,'r1',**recovery()).status,'MUTABLE_OR_UNKNOWN_INPUT')
    def test_flags(self):
        for r in (self.prepare(),self.prepare(bounds={'max_nodes':1}),bounded_commit(Snapshot(),None)):
            self.assertEqual(r.f3,'OPEN')
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
            self.assertFalse(safe_to_promote(r))
