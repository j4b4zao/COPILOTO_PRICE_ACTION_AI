import hashlib
import unittest
from test_f3_int90_import_witness_bundle import fixture_import_witness
from tools.f3_int90_import_witness_bundle import encode_import_bundle
from tools.f3_int91_evidence_registry import BundleRecord
from tools.f3_int93_bundle_mutation_corpus import audit_bundle_mutations,safe_to_promote


class BundleCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob=encode_import_bundle(fixture_import_witness()); cls.record=BundleRecord(blob,hashlib.sha256(blob).hexdigest())
        cls.result=audit_bundle_mutations(cls.record)
    def test_corpus_complete(self):
        self.assertTrue(self.result.complete); self.assertEqual(self.result.failures,())
        self.assertEqual(self.result.status,'BUNDLE_CORPUS_FIXTURE_UNAUTHENTICATED'); self.assertEqual(self.result.checked,25)
    def test_identity_contracts(self):
        observed={label:identity for label,_,identity in self.result.observations}
        self.assertEqual(observed['outer_repack'],'REFERENCE'); self.assertEqual(observed['reverse_pair'],'OBSERVATIONS')
        self.assertEqual(sum(identity!='REJECT' for _,_,identity in self.result.observations),4)
    def test_incomplete_does_not_claim_full_corpus(self):
        r=audit_bundle_mutations(self.record,max_cases=1); self.assertFalse(r.complete); self.assertEqual(r.status,'BUNDLE_CORPUS_LIMIT_REACHED')
    def test_bad_baseline(self):
        self.assertEqual(audit_bundle_mutations(BundleRecord(b'bad','0'*64)).status,'INVALID_BUNDLE_CORPUS_BASELINE')
    def test_bad_bound(self):
        for bound in (False,0,65): self.assertEqual(audit_bundle_mutations(self.record,max_cases=bound).status,'INVALID_BUNDLE_CORPUS_BOUND')
    def test_flags(self):
        r=self.result; self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
