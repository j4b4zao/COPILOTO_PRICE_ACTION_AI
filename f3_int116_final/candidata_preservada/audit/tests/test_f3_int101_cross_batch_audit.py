import hashlib
import unittest
from dataclasses import replace
from test_f3_int96_policy_import_witness import policy_witness_fixture
from tools.f3_int98_policy_bundle_registry import (PolicyBundleRecord, PolicyEvidenceRegistry,
    PolicyEvidenceReceipt, encode_policy_bundle, register_policy_bundles)
from tools.f3_int100_receipt_lineage import build_receipt_lineage
from tools.f3_int101_cross_batch_audit import AuditSegment, audit_cross_batch, safe_to_promote

class CrossBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob=encode_policy_bundle(policy_witness_fixture())
        cls.record=PolicyBundleRecord(blob,hashlib.sha256(blob).hexdigest())
        cls.registration=register_policy_bundles(PolicyEvidenceRegistry(),(cls.record,))
        cls.tip=build_receipt_lineage((cls.record,),cls.registration.receipts,cls.registration.registry).tip
        cls.segment=AuditSegment((cls.record,),cls.registration.receipts,cls.registration.registry,cls.tip)

    def test_valid(self):
        result=audit_cross_batch((self.segment,))
        self.assertEqual(result.status,'CROSS_BATCH_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(result.tips,(self.tip,))
        self.assertEqual(len(result.combined_tip),64)
    def test_deterministic(self):
        self.assertEqual(audit_cross_batch((self.segment,)),audit_cross_batch((self.segment,)))
    def test_expected_combined_tip(self):
        tip=audit_cross_batch((self.segment,)).combined_tip
        self.assertEqual(audit_cross_batch((self.segment,),expected_combined_tip=tip).combined_tip,tip)
    def test_tampered_combined_tip(self):
        self.assertEqual(audit_cross_batch((self.segment,),expected_combined_tip='0'*64).status,'CROSS_BATCH_COMBINED_TIP_MISMATCH')
    def test_bad_expected_tip(self):
        self.assertEqual(audit_cross_batch((self.segment,),expected_combined_tip='bad').status,'INVALID_CROSS_BATCH_EXPECTED_TIP')
    def test_bad_segment_tip(self):
        self.assertEqual(audit_cross_batch((replace(self.segment,expected_tip='bad'),)).status,'INVALID_CROSS_BATCH_SEGMENT_TIP')
    def test_tampered_segment_tip(self):
        self.assertEqual(audit_cross_batch((replace(self.segment,expected_tip='0'*64),)).status,'CROSS_BATCH_SEGMENT_REJECTED:LINEAGE_TIP_MISMATCH')
    def test_duplicate_segment_replay(self):
        self.assertEqual(audit_cross_batch((self.segment,self.segment)).status,'CROSS_BATCH_SEGMENT_REJECTED:LINEAGE_REGISTRY_BOUNDARY_MISMATCH')
    def test_wrong_base(self):
        self.assertEqual(audit_cross_batch((self.segment,),base_registry=self.registration.registry).status,'CROSS_BATCH_SEGMENT_REJECTED:LINEAGE_REGISTRY_BOUNDARY_MISMATCH')
    def test_invalid_base(self):
        self.assertEqual(audit_cross_batch((self.segment,),base_registry=PolicyEvidenceRegistry(('bad',))).status,'INVALID_CROSS_BATCH_BASE')
    def test_invalid_registry(self):
        bad=replace(self.segment,registry=PolicyEvidenceRegistry(('bad',)))
        self.assertEqual(audit_cross_batch((bad,)).status,'INVALID_CROSS_BATCH_REGISTRY')
    def test_orphan_reference(self):
        bad=replace(self.segment,registry=PolicyEvidenceRegistry(('0'*64,)))
        self.assertEqual(audit_cross_batch((bad,)).status,'CROSS_BATCH_SEGMENT_REJECTED:CONSISTENCY_UNREGISTERED_REFERENCE')
    def test_bad_receipt(self):
        receipt=PolicyEvidenceReceipt('0'*64,self.registration.receipts[0].classification)
        self.assertEqual(audit_cross_batch((replace(self.segment,receipts=(receipt,)),)).status,'CROSS_BATCH_SEGMENT_REJECTED:CONSISTENCY_RECEIPT_MISMATCH')
    def test_corrupted_bundle(self):
        bad=PolicyBundleRecord(self.record.blob+b'bad',self.record.sha256)
        self.assertEqual(audit_cross_batch((replace(self.segment,records=(bad,)),)).status,'CROSS_BATCH_SEGMENT_REJECTED:INVALID_CONSISTENCY_BUNDLE')
    def test_invalid_segments(self):
        for x in ((),[],(None,),tuple([self.segment]*17)):
            self.assertEqual(audit_cross_batch(x).status,'INVALID_CROSS_BATCH_SEGMENTS')
    def test_read_only(self):
        old=self.segment
        audit_cross_batch((self.segment,))
        self.assertEqual(old,self.segment)
    def test_locks(self):
        result=audit_cross_batch((self.segment,))
        self.assertEqual(result.f3,'OPEN')
        self.assertFalse(safe_to_promote(result))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(result,k),False)

if __name__=='__main__': unittest.main()
