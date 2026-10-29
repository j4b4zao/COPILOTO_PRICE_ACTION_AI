import hashlib
import unittest
from dataclasses import replace
from test_f3_int96_policy_import_witness import policy_witness_fixture
from tools.f3_int98_policy_bundle_registry import (PolicyBundleRecord, PolicyEvidenceRegistry,
    PolicyEvidenceReceipt, encode_policy_bundle, register_policy_bundles)
from tools.f3_int100_receipt_lineage import build_receipt_lineage
from tools.f3_int101_cross_batch_audit import AuditSegment
from tools.f3_int102_transcript_commitment import commit_transcript, safe_to_promote

class TranscriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob = encode_policy_bundle(policy_witness_fixture())
        cls.record = PolicyBundleRecord(blob, hashlib.sha256(blob).hexdigest())
        cls.reg = register_policy_bundles(PolicyEvidenceRegistry(), (cls.record,))
        cls.tip = build_receipt_lineage((cls.record,), cls.reg.receipts, cls.reg.registry).tip
        cls.segment = AuditSegment((cls.record,), cls.reg.receipts, cls.reg.registry, cls.tip)

    def test_valid(self):
        r=commit_transcript((self.segment,))
        self.assertEqual(r.status,'TRANSCRIPT_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(len(r.digest),64)
        self.assertEqual(r.count,1)
    def test_determinism(self):
        self.assertEqual(commit_transcript((self.segment,)),commit_transcript((self.segment,)))
    def test_matching_anchor(self):
        digest=commit_transcript((self.segment,)).digest
        self.assertEqual(commit_transcript((self.segment,),expected_digest=digest).digest,digest)
    def test_wrong_anchor(self):
        self.assertEqual(commit_transcript((self.segment,),expected_digest='0'*64).status,'TRANSCRIPT_DIGEST_MISMATCH')
    def test_invalid_anchor(self):
        self.assertEqual(commit_transcript((self.segment,),expected_digest='invalid').status,'INVALID_TRANSCRIPT_EXPECTED_DIGEST')
    def test_bad_base(self):
        self.assertEqual(commit_transcript((self.segment,),base_registry=PolicyEvidenceRegistry(('bad',))).status,'INVALID_TRANSCRIPT_BASE')
    def test_wrong_base_boundary(self):
        self.assertIn('LINEAGE_REGISTRY_BOUNDARY_MISMATCH',commit_transcript((self.segment,),base_registry=self.reg.registry).status)
    def test_replayed_segment(self):
        self.assertIn('LINEAGE_REGISTRY_BOUNDARY_MISMATCH',commit_transcript((self.segment,self.segment)).status)
    def test_invalid_segments(self):
        for segments in ((),[],(None,),tuple([self.segment]*17)):
            self.assertTrue(commit_transcript(segments).status.startswith('TRANSCRIPT_AUDIT_REJECTED:'))
    def test_bad_tip(self):
        self.assertIn('LINEAGE_TIP_MISMATCH',commit_transcript((replace(self.segment,expected_tip='0'*64),)).status)
    def test_receipt_mutation(self):
        bad=PolicyEvidenceReceipt('0'*64,self.reg.receipts[0].classification)
        self.assertIn('CONSISTENCY_RECEIPT_MISMATCH',commit_transcript((replace(self.segment,receipts=(bad,)),)).status)
    def test_corrupt_blob(self):
        bad=PolicyBundleRecord(self.record.blob+b'!',self.record.sha256)
        self.assertIn('INVALID_CONSISTENCY_BUNDLE',commit_transcript((replace(self.segment,records=(bad,)),)).status)
    def test_read_only(self):
        original=self.segment
        commit_transcript((original,))
        self.assertEqual(original,self.segment)
    def test_locks(self):
        r=commit_transcript((self.segment,))
        self.assertEqual(r.f3,'OPEN')
        self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)

if __name__=='__main__': unittest.main()
