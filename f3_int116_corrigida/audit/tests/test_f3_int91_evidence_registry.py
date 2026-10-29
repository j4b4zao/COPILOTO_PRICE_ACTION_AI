import hashlib
import unittest
from dataclasses import replace
from test_f3_int90_import_witness_bundle import fixture_import_witness,rewrite_bundle
from tools.f3_int72_atomic_witness_batch_simulator import Registry
from tools.f3_int90_import_witness_bundle import encode_import_bundle
from tools.f3_int91_evidence_registry import EvidenceRegistry,BundleRecord,describe_bundle,register_evidence_batch,safe_to_promote


def record(blob): return BundleRecord(blob,hashlib.sha256(blob).hexdigest())


class EvidenceRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.witness=fixture_import_witness(); cls.bundle=record(encode_import_bundle(cls.witness))
    def test_registration(self):
        r=register_evidence_batch(EvidenceRegistry(),(self.bundle,))
        self.assertEqual(r.status,'EVIDENCE_REGISTERED_FIXTURE_UNAUTHENTICATED'); self.assertEqual(len(r.registry.reference_ids),1)
    def test_reference_replay_atomic(self):
        s=EvidenceRegistry(); r=register_evidence_batch(s,(self.bundle,self.bundle))
        self.assertEqual(r.status,'EVIDENCE_REFERENCE_REPLAY'); self.assertIs(r.registry,s); self.assertEqual(r.receipts,())
    def test_outer_repacking_preserves_identity(self):
        repacked=record(rewrite_bundle(self.bundle.blob,lambda files:None))
        r=register_evidence_batch(EvidenceRegistry(),(self.bundle,repacked))
        self.assertEqual(r.status,'EVIDENCE_REFERENCE_REPLAY')
    def test_pair_orientation_has_same_observables(self):
        reversed_witness=replace(self.witness,left=self.witness.right,right=self.witness.left)
        reversed_bundle=record(encode_import_bundle(reversed_witness))
        a=describe_bundle(self.bundle.blob,self.bundle.sha256); b=describe_bundle(reversed_bundle.blob,reversed_bundle.sha256)
        self.assertNotEqual(a.reference_id,b.reference_id); self.assertEqual(a.observable_id,b.observable_id)
        s=EvidenceRegistry(); r=register_evidence_batch(s,(self.bundle,reversed_bundle))
        self.assertEqual(r.status,'EVIDENCE_OBSERVABLE_REPLAY'); self.assertIs(r.registry,s)
    def test_invalid_tail_atomic(self):
        s=EvidenceRegistry(); r=register_evidence_batch(s,(self.bundle,record(b'bad')))
        self.assertEqual(r.status,'EVIDENCE_BUNDLE_REJECTED'); self.assertIs(r.registry,s); self.assertEqual(r.receipts,())
    def test_cross_batch_replay(self):
        s=register_evidence_batch(EvidenceRegistry(),(self.bundle,)).registry
        r=register_evidence_batch(s,(self.bundle,)); self.assertEqual(r.status,'EVIDENCE_REFERENCE_REPLAY'); self.assertIs(r.registry,s)
    def test_consumed_witness_registry_rejected(self):
        self.assertEqual(register_evidence_batch(Registry(),(self.bundle,)).status,'INVALID_TYPED_EVIDENCE_REGISTRY')
    def test_wrong_namespace(self):
        self.assertEqual(register_evidence_batch(EvidenceRegistry(namespace='other'),(self.bundle,)).status,'INVALID_TYPED_EVIDENCE_REGISTRY')
    def test_unpaired_registry_ids(self):
        self.assertEqual(register_evidence_batch(EvidenceRegistry(('0'*64,),()),(self.bundle,)).status,'INVALID_TYPED_EVIDENCE_REGISTRY')
    def test_reset_limit(self):
        register_evidence_batch(EvidenceRegistry(),(self.bundle,))
        self.assertEqual(register_evidence_batch(EvidenceRegistry(),(self.bundle,)).status,'EVIDENCE_REGISTERED_FIXTURE_UNAUTHENTICATED')
    def test_byte_bound(self):
        self.assertEqual(register_evidence_batch(EvidenceRegistry(),(self.bundle,),max_total_bytes=1).status,'EVIDENCE_TOTAL_BYTE_LIMIT')
    def test_invalid_bound(self):
        self.assertEqual(register_evidence_batch(EvidenceRegistry(),(self.bundle,),max_total_bytes=False).status,'INVALID_EVIDENCE_BYTE_BOUND')
    def test_flags(self):
        r=register_evidence_batch(EvidenceRegistry(),(self.bundle,)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
