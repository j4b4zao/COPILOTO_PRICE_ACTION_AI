import hashlib
import json
import unittest
from test_f3_int53_interleaving import recovery
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int68_crash_witness_simulator import find_crash_witness
from tools.f3_int69_crash_minimizer_simulator import minimize_crash_witness
from tools.f3_int70_crash_witness_codec import encode_witness
from tools.f3_int72_atomic_witness_batch_simulator import Registry, EncodedRecord, assess_batch, safe_to_promote


def record(blob): return EncodedRecord(blob,hashlib.sha256(blob).hexdigest())


class AtomicBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=[]
        for a,b in (('a','b'),('c','d')):
            requests=(request(a,**recovery(6)),request(b,**recovery(5)))
            blob=encode_witness(minimize_crash_witness(find_crash_witness(requests).witness).witness)
            cls.records.append(record(blob))
        cls.records=tuple(cls.records)
    def test_valid_batch(self):
        r=assess_batch(Registry(),self.records)
        self.assertEqual(r.status,'BATCH_WITNESS_FIXTURE_UNAUTHENTICATED'); self.assertEqual(len(r.registry.digests),2)
    def test_duplicate_in_batch(self):
        s=Registry(); r=assess_batch(s,(self.records[0],)*2)
        self.assertEqual(r.status,'REPLAYED_CANONICAL_WITNESS'); self.assertIs(r.registry,s)
    def test_cross_batch_replay(self):
        s=assess_batch(Registry(),self.records[:1]).registry; r=assess_batch(s,self.records[:1])
        self.assertEqual(r.status,'REPLAYED_CANONICAL_WITNESS'); self.assertIs(r.registry,s)
    def test_formatting_does_not_evade_replay(self):
        pretty=json.dumps(json.loads(self.records[0].payload),indent=2).encode()
        r=assess_batch(Registry(),(self.records[0],record(pretty)))
        self.assertEqual(r.status,'REPLAYED_CANONICAL_WITNESS')
    def test_invalid_tail_atomic(self):
        s=Registry(); r=assess_batch(s,(self.records[0],record(b'{}')))
        self.assertEqual(r.status,'BATCH_WITNESS_REPLAY_REJECTED'); self.assertIs(r.registry,s)
    def test_hash_mismatch_tail_atomic(self):
        s=Registry(); r=assess_batch(s,(self.records[0],EncodedRecord(self.records[1].payload,'0'*64)))
        self.assertEqual(r.status,'RECORD_DIGEST_MISMATCH'); self.assertIs(r.registry,s)
    def test_registry_reset_limit(self):
        assess_batch(Registry(),self.records[:1])
        self.assertEqual(assess_batch(Registry(),self.records[:1]).status,'BATCH_WITNESS_FIXTURE_UNAUTHENTICATED')
    def test_memory_bound(self):
        self.assertEqual(assess_batch(Registry(),self.records,max_memory=1).status,'REGISTRY_LIMIT_EXCEEDED')
    def test_byte_bound(self):
        self.assertEqual(assess_batch(Registry(),self.records,max_total_bytes=1).status,'BATCH_BYTE_LIMIT_EXCEEDED')
    def test_record_bound(self):
        self.assertEqual(assess_batch(Registry(),self.records,max_records=1).status,'INVALID_WITNESS_BATCH')
    def test_invalid_registry(self):
        for s in (None,Registry([]),Registry(('bad',)),Registry(('0'*64,)*2)):
            self.assertEqual(assess_batch(s,self.records).status,'INVALID_WITNESS_REGISTRY')
    def test_invalid_bounds(self):
        for kwargs in ({'max_memory':False},{'max_records':0},{'max_total_bytes':1048577}):
            self.assertEqual(assess_batch(Registry(),self.records,**kwargs).status,'INVALID_BATCH_BOUND')
    def test_invalid_record(self):
        self.assertEqual(assess_batch(Registry(),(EncodedRecord(b'{}',False),)).status,'INVALID_ENCODED_RECORD')
    def test_flags(self):
        for r in (assess_batch(Registry(),self.records),assess_batch(Registry(),self.records*2)):
            self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
