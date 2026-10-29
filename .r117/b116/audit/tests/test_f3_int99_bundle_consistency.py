import hashlib
import unittest
from test_f3_int96_policy_import_witness import policy_witness_fixture
from tools.f3_int98_policy_bundle_registry import (
    PolicyBundleRecord, PolicyEvidenceRegistry, PolicyEvidenceReceipt,
    encode_policy_bundle, register_policy_bundles,
)
from tools.f3_int99_bundle_consistency import verify_policy_bundle_receipts, safe_to_promote

class BundleConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob = encode_policy_bundle(policy_witness_fixture())
        cls.record = PolicyBundleRecord(blob, hashlib.sha256(blob).hexdigest())
        cls.registration = register_policy_bundles(PolicyEvidenceRegistry(), (cls.record,))

    def verify(self, records=None, receipts=None, registry=None):
        return verify_policy_bundle_receipts(
            (self.record,) if records is None else records,
            self.registration.receipts if receipts is None else receipts,
            self.registration.registry if registry is None else registry,
        )

    def test_consistent(self):
        result = self.verify()
        self.assertEqual(result.status, 'CONSISTENT_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(result.references, self.registration.registry.reference_ids)
    def test_unregistered(self):
        self.assertEqual(self.verify(registry=PolicyEvidenceRegistry()).status, 'CONSISTENCY_UNREGISTERED_REFERENCE')
    def test_wrong_reference(self):
        self.assertEqual(self.verify(receipts=(PolicyEvidenceReceipt('0'*64, self.registration.receipts[0].classification),)).status, 'CONSISTENCY_RECEIPT_MISMATCH')
    def test_wrong_classification(self):
        self.assertEqual(self.verify(receipts=(PolicyEvidenceReceipt(self.registration.receipts[0].reference_id, 'FORGED'),)).status, 'CONSISTENCY_RECEIPT_MISMATCH')
    def test_duplicate(self):
        self.assertEqual(self.verify(records=(self.record,self.record), receipts=self.registration.receipts*2).status, 'CONSISTENCY_DUPLICATE_REFERENCE')
    def test_corrupt_bundle(self):
        bad=PolicyBundleRecord(self.record.blob+b'X',self.record.sha256)
        self.assertEqual(self.verify(records=(bad,)).status, 'INVALID_CONSISTENCY_BUNDLE')
    def test_invalid_registry(self):
        self.assertEqual(self.verify(registry=PolicyEvidenceRegistry(('bad',))).status, 'INVALID_POLICY_REGISTRY')
    def test_invalid_batch(self):
        self.assertEqual(self.verify(records=()).status, 'INVALID_CONSISTENCY_BATCH')
    def test_invalid_record(self):
        self.assertEqual(self.verify(records=('bad',)).status, 'INVALID_CONSISTENCY_RECORD')
    def test_locks(self):
        result=self.verify()
        self.assertEqual(result.f3,'OPEN')
        self.assertFalse(safe_to_promote(result))
        for field in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(result,field),False)

if __name__=='__main__': unittest.main()
