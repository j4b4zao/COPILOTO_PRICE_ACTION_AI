import hashlib
import json
import unittest
from test_f3_int53_interleaving import recovery
from test_f3_int76_segmented_lineage import fixture_package
from test_f3_int78_verified_envelope import rewrite_record
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int68_crash_witness_simulator import find_crash_witness
from tools.f3_int69_crash_minimizer_simulator import minimize_crash_witness
from tools.f3_int70_crash_witness_codec import encode_witness
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int81_package_bound_witness import assess_package_witness,safe_to_promote


def witness_blob(a='a',b='b'):
    requests=(request(a,**recovery(6)),request(b,**recovery(5)))
    return encode_witness(minimize_crash_witness(find_crash_witness(requests).witness).witness)


class PackageWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob=witness_blob(); cls.pin=hashlib.sha256(cls.blob).hexdigest(); cls.path='evidence/witness.json'
        cls.record=rewrite_record(fixture_package(53,528),{cls.path:cls.blob})
    def test_bound_witness(self):
        r=assess_package_witness(self.record,self.path,self.pin)
        self.assertEqual(r.status,'PACKAGE_BOUND_WITNESS_FIXTURE_UNAUTHENTICATED')
        self.assertEqual((r.package_sha256,r.payload_sha256,r.canonical_sha256),(self.record.sha256,self.pin,self.pin))
    def test_formatting_keeps_canonical_pin(self):
        pretty=json.dumps(json.loads(self.blob),indent=2).encode()
        package=rewrite_record(fixture_package(53,528),{self.path:pretty})
        r=assess_package_witness(package,self.path,self.pin)
        self.assertEqual(r.canonical_sha256,self.pin); self.assertNotEqual(r.payload_sha256,self.pin)
    def test_wrong_pin(self):
        r=assess_package_witness(self.record,self.path,'0'*64)
        self.assertEqual(r.status,'PACKAGE_WITNESS_PIN_MISMATCH'); self.assertEqual(r.payload,b'')
    def test_package_hash_binding(self):
        bad=PackageRecord(self.record.stage,self.record.blob,'0'*64)
        self.assertEqual(assess_package_witness(bad,self.path,self.pin).status,'PACKAGE_WITNESS_ENVELOPE_DIGEST_MISMATCH')
    def test_missing_file(self): self.assertEqual(assess_package_witness(self.record,'evidence/missing.json',self.pin).status,'MISSING_PACKAGE_WITNESS')
    def test_invalid_paths(self):
        for path in ('../witness.json','/witness.json','evidence/witness.py',False):
            self.assertEqual(assess_package_witness(self.record,path,self.pin).status,'INVALID_WITNESS_PATH')
    def test_wrong_json_schema(self):
        record=rewrite_record(fixture_package(53,528),{self.path:b'{}'})
        self.assertEqual(assess_package_witness(record,self.path,self.pin).status,'PACKAGE_WITNESS_REPLAY_REJECTED')
    def test_invalid_pin(self):
        for pin in (None,False,'pin','A'*64):
            self.assertEqual(assess_package_witness(self.record,self.path,pin).status,'INVALID_CANONICAL_PIN')
    def test_wrong_record_type(self): self.assertEqual(assess_package_witness(None,self.path,self.pin).status,'INVALID_PACKAGE_WITNESS_RECORD')
    def test_flags(self):
        for r in (assess_package_witness(self.record,self.path,self.pin),assess_package_witness(self.record,self.path,'0'*64)):
            self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
