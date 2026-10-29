import hashlib
import unittest
from test_f3_int96_policy_import_witness import policy_witness_fixture
from tools.f3_int98_policy_bundle_registry import (PolicyBundleRecord, PolicyEvidenceRegistry,
    PolicyEvidenceReceipt, encode_policy_bundle, register_policy_bundles)
from tools.f3_int100_receipt_lineage import (build_receipt_lineage, verify_receipt_lineage, safe_to_promote)

class ReceiptLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob = encode_policy_bundle(policy_witness_fixture())
        cls.record = PolicyBundleRecord(blob, hashlib.sha256(blob).hexdigest())
        cls.result = register_policy_bundles(PolicyEvidenceRegistry(), (cls.record,))

    def build(self, **kwargs):
        return build_receipt_lineage(kwargs.get('records', (self.record,)),
            kwargs.get('receipts', self.result.receipts), kwargs.get('registry', self.result.registry),
            base_registry=kwargs.get('base_registry', None))

    def test_valid(self):
        result = self.build()
        self.assertEqual(result.status, 'LINEAGE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(len(result.chain), 1)
        self.assertEqual(result.tip, result.chain[-1])
    def test_deterministic(self):
        self.assertEqual(self.build(), self.build())
    def test_tip_verify(self):
        tip = self.build().tip
        self.assertEqual(verify_receipt_lineage((self.record,),self.result.receipts,self.result.registry,tip).tip,tip)
    def test_tip_tamper(self):
        self.assertEqual(verify_receipt_lineage((self.record,),self.result.receipts,self.result.registry,'0'*64).status,'LINEAGE_TIP_MISMATCH')
    def test_invalid_tip(self):
        self.assertEqual(verify_receipt_lineage((self.record,),self.result.receipts,self.result.registry,'bad').status,'INVALID_EXPECTED_TIP')
    def test_wrong_receipt(self):
        bad = PolicyEvidenceReceipt('0'*64, self.result.receipts[0].classification)
        self.assertEqual(self.build(receipts=(bad,)).status,'CONSISTENCY_RECEIPT_MISMATCH')
    def test_invalid_registry(self):
        self.assertEqual(self.build(registry=PolicyEvidenceRegistry(('bad',))).status,'INVALID_POLICY_REGISTRY')
    def test_boundary(self):
        self.assertEqual(self.build(base_registry=self.result.registry).status,'LINEAGE_REGISTRY_BOUNDARY_MISMATCH')
    def test_extra_registry(self):
        extra=PolicyEvidenceRegistry(self.result.registry.reference_ids+('0'*64,))
        self.assertEqual(self.build(registry=extra).status,'LINEAGE_REGISTRY_BOUNDARY_MISMATCH')
    def test_bad_base(self):
        self.assertEqual(self.build(base_registry=PolicyEvidenceRegistry(('bad',))).status,'INVALID_BASE_REGISTRY')
    def test_empty(self):
        self.assertEqual(self.build(records=()).status,'INVALID_LINEAGE_BATCH')
    def test_corrupt_blob(self):
        bad=PolicyBundleRecord(self.record.blob+b'x',self.record.sha256)
        self.assertEqual(self.build(records=(bad,)).status,'INVALID_CONSISTENCY_BUNDLE')
    def test_locks(self):
        result=self.build()
        self.assertEqual(result.f3,'OPEN')
        self.assertFalse(safe_to_promote(result))
        for name in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(result,name),False)

if __name__ == '__main__': unittest.main()
