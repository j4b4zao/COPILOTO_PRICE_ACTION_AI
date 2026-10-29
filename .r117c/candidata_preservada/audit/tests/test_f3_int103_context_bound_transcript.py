import hashlib
import unittest
from dataclasses import replace
from test_f3_int96_policy_import_witness import policy_witness_fixture
from tools.f3_int98_policy_bundle_registry import (PolicyBundleRecord, PolicyEvidenceRegistry,
    encode_policy_bundle, register_policy_bundles)
from tools.f3_int100_receipt_lineage import build_receipt_lineage
from tools.f3_int101_cross_batch_audit import AuditSegment
from tools.f3_int103_context_bound_transcript import bind_transcript_context, safe_to_promote

class ContextBoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob=encode_policy_bundle(policy_witness_fixture())
        record=PolicyBundleRecord(blob,hashlib.sha256(blob).hexdigest())
        reg=register_policy_bundles(PolicyEvidenceRegistry(),(record,))
        tip=build_receipt_lineage((record,),reg.receipts,reg.registry).tip
        cls.segment=AuditSegment((record,),reg.receipts,reg.registry,tip)

    def bind(self,**kwargs):
        return bind_transcript_context((self.segment,),context='audit:fixture/A',**kwargs)

    def test_success(self):
        r=self.bind()
        self.assertEqual(r.status,'CONTEXT_BOUND_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(len(r.digest),64)
    def test_determinism(self):
        self.assertEqual(self.bind(),self.bind())
    def test_context_separation(self):
        a=self.bind()
        b=bind_transcript_context((self.segment,),context='audit:fixture/B')
        self.assertNotEqual(a.digest,b.digest)
        self.assertEqual(a.transcript_digest,b.transcript_digest)
    def test_cross_context_replay(self):
        a=self.bind()
        b=bind_transcript_context((self.segment,),context='audit:fixture/B',expected_digest=a.digest)
        self.assertEqual(b.status,'CONTEXT_DIGEST_MISMATCH')
    def test_correct_expected(self):
        a=self.bind()
        self.assertEqual(self.bind(expected_digest=a.digest),a)
    def test_wrong_expected(self):
        self.assertEqual(self.bind(expected_digest='0'*64).status,'CONTEXT_DIGEST_MISMATCH')
    def test_invalid_expected(self):
        for value in ('bad','G'*64,42,True):
            with self.subTest(value=value):
                self.assertEqual(self.bind(expected_digest=value).status,'INVALID_EXPECTED_CONTEXT_DIGEST')
    def test_invalid_context_types(self):
        for value in (None,0,True,b'fixture',[],{}):
            with self.subTest(value=value):
                self.assertEqual(bind_transcript_context((self.segment,),context=value).status,'INVALID_CONTEXT')
    def test_invalid_context_strings(self):
        for value in ('',' ',' a','a ','a\nb','é','a'*129,'a\\b','a\x00b'):
            with self.subTest(value=value):
                self.assertEqual(bind_transcript_context((self.segment,),context=value).status,'INVALID_CONTEXT')
    def test_context_case_sensitive(self):
        a=self.bind().digest
        b=bind_transcript_context((self.segment,),context='AUDIT:fixture/A').digest
        self.assertNotEqual(a,b)
    def test_invalid_transcript(self):
        r=bind_transcript_context((replace(self.segment,expected_tip='0'*64),),context='audit:A')
        self.assertIn('TRANSCRIPT_REJECTED:',r.status)
    def test_empty_segments(self):
        self.assertIn('TRANSCRIPT_REJECTED:',bind_transcript_context((),context='audit:A').status)
    def test_no_mutation(self):
        before=self.segment
        self.bind()
        self.assertEqual(before,self.segment)
    def test_lock_flags(self):
        for r in (self.bind(),bind_transcript_context((),context='bad')):
            self.assertEqual(r.f3,'OPEN')
            self.assertFalse(safe_to_promote(r))
            for key in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,key),False)

if __name__=='__main__': unittest.main()
