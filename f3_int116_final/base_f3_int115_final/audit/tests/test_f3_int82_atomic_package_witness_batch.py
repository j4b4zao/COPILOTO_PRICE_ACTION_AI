import hashlib
import json
import unittest
from dataclasses import replace
from test_f3_int76_segmented_lineage import fixture_package
from test_f3_int78_verified_envelope import rewrite_record
from test_f3_int81_package_bound_witness import witness_blob
from tools.f3_int72_atomic_witness_batch_simulator import Registry
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int82_atomic_package_witness_batch import PackageWitnessRequest,assess_package_batch,safe_to_promote


class PackageBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests=[]
        for i,(a,b) in enumerate((('a','b'),('c','d'))):
            blob=witness_blob(a,b); pin=hashlib.sha256(blob).hexdigest(); path=f'evidence/witness{i}.json'
            record=rewrite_record(fixture_package(53+i,528+2*i),{path:blob})
            cls.requests.append(PackageWitnessRequest(record,path,pin))
        cls.requests=tuple(cls.requests)
    def test_atomic_success(self):
        r=assess_package_batch(Registry(),self.requests)
        self.assertEqual(r.status,'ATOMIC_PACKAGE_WITNESS_BATCH_FIXTURE_UNAUTHENTICATED'); self.assertEqual(len(r.registry.digests),2)
        self.assertEqual(len(r.bindings),2)
    def test_duplicate_canonical_witness(self):
        s=Registry(); r=assess_package_batch(s,(self.requests[0],)*2)
        self.assertEqual(r.status,'REPLAYED_CANONICAL_WITNESS'); self.assertIs(r.registry,s); self.assertEqual(r.bindings,())
    def test_different_package_same_witness(self):
        first=self.requests[0]
        changed=rewrite_record(first.record,{'docs/extra.txt':b'changed transport'})
        s=Registry(); r=assess_package_batch(s,(first,replace(first,record=changed)))
        self.assertEqual(r.status,'REPLAYED_CANONICAL_WITNESS'); self.assertIs(r.registry,s)
    def test_formatting_does_not_evade_registry(self):
        first=self.requests[0]
        from io import BytesIO
        import zipfile
        with zipfile.ZipFile(BytesIO(first.record.blob)) as archive: payload=archive.read(first.path)
        changed=rewrite_record(first.record,{first.path:json.dumps(json.loads(payload),indent=2).encode()})
        self.assertEqual(assess_package_batch(Registry(),(first,replace(first,record=changed))).status,'REPLAYED_CANONICAL_WITNESS')
    def test_wrong_pin_tail_atomic(self):
        s=Registry(); requests=(self.requests[0],replace(self.requests[1],canonical_pin='0'*64))
        r=assess_package_batch(s,requests); self.assertEqual(r.status,'BATCH_PACKAGE_WITNESS_PIN_MISMATCH')
        self.assertIs(r.registry,s); self.assertEqual(r.bindings,())
    def test_wrong_package_digest_tail_atomic(self):
        s=Registry(); last=self.requests[1]; record=PackageRecord(last.record.stage,last.record.blob,'0'*64)
        r=assess_package_batch(s,(self.requests[0],replace(last,record=record)))
        self.assertEqual(r.status,'BATCH_PACKAGE_WITNESS_ENVELOPE_DIGEST_MISMATCH'); self.assertIs(r.registry,s)
    def test_cross_batch_replay(self):
        s=assess_package_batch(Registry(),self.requests[:1]).registry
        r=assess_package_batch(s,self.requests[:1]); self.assertEqual(r.status,'REPLAYED_CANONICAL_WITNESS'); self.assertIs(r.registry,s)
    def test_reset_registry_limit_demonstrated(self):
        assess_package_batch(Registry(),self.requests[:1])
        self.assertEqual(assess_package_batch(Registry(),self.requests[:1]).status,'ATOMIC_PACKAGE_WITNESS_BATCH_FIXTURE_UNAUTHENTICATED')
    def test_byte_limit(self):
        self.assertEqual(assess_package_batch(Registry(),self.requests,max_package_bytes=1).status,'PACKAGE_BATCH_BYTE_LIMIT')
    def test_invalid_registry(self):
        self.assertEqual(assess_package_batch(Registry([]),self.requests).status,'INVALID_WITNESS_REGISTRY')
    def test_invalid_requests(self):
        for requests in ((),[],(None,),self.requests*9):
            self.assertEqual(assess_package_batch(Registry(),requests).status,'INVALID_PACKAGE_WITNESS_BATCH')
    def test_invalid_bound(self):
        self.assertEqual(assess_package_batch(Registry(),self.requests,max_package_bytes=False).status,'INVALID_PACKAGE_BATCH_BOUND')
    def test_flags(self):
        r=assess_package_batch(Registry(),self.requests); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
