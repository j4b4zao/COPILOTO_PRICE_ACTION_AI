import hashlib
import unittest
from unittest.mock import patch
from dataclasses import replace
from test_f3_int76_segmented_lineage import fixture_package
from test_f3_int78_verified_envelope import rewrite_record
from test_f3_int90_import_witness_bundle import fixture_import_witness
from tools.f3_int90_import_witness_bundle import encode_import_bundle
from tools.f3_int91_evidence_registry import describe_bundle
from tools.f3_int94_attached_evidence_verifier import assess_attached_evidence,safe_to_promote


class AttachedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob=encode_import_bundle(fixture_import_witness()); cls.bundle_pin=hashlib.sha256(cls.blob).hexdigest()
        cls.observable_pin=describe_bundle(cls.blob,cls.bundle_pin).observable_id
        cls.path='evidence/example.witnessbundle'
        cls.record=rewrite_record(fixture_package(53,528),{cls.path:cls.blob})
    def test_entire_chain(self):
        r=assess_attached_evidence(self.record,self.path,self.bundle_pin,self.observable_pin)
        self.assertEqual(r.status,'ATTACHED_EVIDENCE_REPLAYED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual((r.package_sha256,r.bundle_sha256,r.observable_id),(self.record.sha256,self.bundle_pin,self.observable_pin))
        self.assertEqual(r.classification,'ORDER_ONLY')
    def test_package_pin(self):
        bad=replace(self.record,sha256='0'*64)
        self.assertEqual(assess_attached_evidence(bad,self.path,self.bundle_pin,self.observable_pin).status,'ATTACHED_ENVELOPE_DIGEST_MISMATCH')
    def test_bundle_pin(self):
        self.assertEqual(assess_attached_evidence(self.record,self.path,'0'*64,self.observable_pin).status,'ATTACHED_BUNDLE_PIN_MISMATCH')
    def test_observable_pin(self):
        r=assess_attached_evidence(self.record,self.path,self.bundle_pin,'0'*64)
        self.assertEqual(r.status,'ATTACHED_OBSERVABLE_PIN_MISMATCH'); self.assertEqual(r.reference_id,'')
    def test_attached_bad_bundle_rehashed_package(self):
        bad=b'bad'; pin=hashlib.sha256(bad).hexdigest(); record=rewrite_record(self.record,{self.path:bad})
        self.assertEqual(assess_attached_evidence(record,self.path,pin,self.observable_pin).status,'ATTACHED_BUNDLE_REPLAY_REJECTED')
    def test_missing_attachment(self):
        self.assertEqual(assess_attached_evidence(self.record,'missing.witnessbundle',self.bundle_pin,self.observable_pin).status,'MISSING_ATTACHED_EVIDENCE')
    def test_invalid_paths(self):
        for path in ('../e.witnessbundle','/e.witnessbundle','example.zip',False):
            self.assertEqual(assess_attached_evidence(self.record,path,self.bundle_pin,self.observable_pin).status,'INVALID_ATTACHED_EVIDENCE_PATH')
    def test_invalid_pins(self):
        self.assertEqual(assess_attached_evidence(self.record,self.path,False,self.observable_pin).status,'INVALID_ATTACHED_EVIDENCE_PIN')
    def test_attachment_has_its_own_byte_cap(self):
        with patch('tools.f3_int94_attached_evidence_verifier.MAX_BUNDLE_BYTES',1):
            self.assertEqual(assess_attached_evidence(self.record,self.path,self.bundle_pin,self.observable_pin).status,'ATTACHED_BUNDLE_BYTE_LIMIT')
    def test_invalid_record(self):
        self.assertEqual(assess_attached_evidence(None,self.path,self.bundle_pin,self.observable_pin).status,'INVALID_ATTACHED_EVIDENCE_RECORD')
    def test_flags(self):
        r=assess_attached_evidence(self.record,self.path,self.bundle_pin,self.observable_pin)
        self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
