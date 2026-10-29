import hashlib
import io
import json
import unittest
import zipfile
from test_f3_int96_policy_import_witness import policy_witness_fixture
from tools.f3_int98_policy_bundle_registry import *
from tools.f3_int90_import_witness_bundle import assess_import_bundle

class PolicyBundleRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.witness=policy_witness_fixture()
        cls.blob=encode_policy_bundle(cls.witness)
        cls.digest=hashlib.sha256(cls.blob).hexdigest()
    def altered(self,modify):
        with zipfile.ZipFile(io.BytesIO(self.blob)) as z:
            files={n:z.read(n) for n in z.namelist()}
        modify(files)
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            for k,v in files.items(): z.writestr(k,v)
        return out.getvalue()
    def rejected(self,blob):
        with self.assertRaises(ValueError): decode_policy_bundle(blob,hashlib.sha256(blob).hexdigest())
    def test_roundtrip(self): self.assertEqual(decode_policy_bundle(self.blob,self.digest),self.witness)
    def test_deterministic(self): self.assertEqual(encode_policy_bundle(self.witness),self.blob)
    def test_legacy_rejects_schema2(self): self.assertEqual(assess_import_bundle(self.blob,self.digest).status,'IMPORT_BUNDLE_REJECTED')
    def test_digest_tamper(self):
        with self.assertRaises(ValueError): decode_policy_bundle(self.blob,'0'*64)
    def test_wrong_schema(self):
        def edit(f):
            p=json.loads(f['bundle_manifest.json']);p['schema']=1;f['bundle_manifest.json']=json.dumps(p).encode()
        self.rejected(self.altered(edit))
    def test_policy_tamper(self):
        def edit(f):
            p=json.loads(f['witness.json']);p['initial']['policy']['max_files']=999
            f['witness.json']=json.dumps(p).encode()
        self.rejected(self.altered(edit))
    def test_catalog_tamper(self):
        self.rejected(self.altered(lambda f:f.update({next(k for k in f if k.startswith('catalog/')):b'changed'})))
    def test_extra_member(self): self.rejected(self.altered(lambda f:f.update({'extra.txt':b'x'})))
    def test_missing_member(self): self.rejected(self.altered(lambda f:f.pop(next(k for k in f if k.startswith('catalog/')))))
    def test_bad_type(self):
        with self.assertRaises(ValueError): decode_policy_bundle('bad',self.digest)
    def test_register(self):
        r=register_policy_bundles(PolicyEvidenceRegistry(),(PolicyBundleRecord(self.blob,self.digest),))
        self.assertEqual(r.status,'POLICY_EVIDENCE_REGISTERED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(len(r.registry.reference_ids),1)
        self.assertEqual(r.f3,'OPEN')
        self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
    def test_replay_rejected(self):
        record=PolicyBundleRecord(self.blob,self.digest)
        r=register_policy_bundles(PolicyEvidenceRegistry(),(record,))
        self.assertEqual(register_policy_bundles(r.registry,(record,)).status,'POLICY_REFERENCE_REPLAY')
    def test_atomic_rejection(self):
        good=PolicyBundleRecord(self.blob,self.digest)
        bad=PolicyBundleRecord(self.blob,'0'*64)
        r=register_policy_bundles(PolicyEvidenceRegistry(),(good,bad))
        self.assertEqual(r.status,'POLICY_BUNDLE_REJECTED')
        self.assertEqual(r.registry,PolicyEvidenceRegistry())
    def test_duplicate_batch(self):
        record=PolicyBundleRecord(self.blob,self.digest)
        self.assertEqual(register_policy_bundles(PolicyEvidenceRegistry(),(record,record)).status,'POLICY_REFERENCE_REPLAY')
    def test_bound(self):
        record=PolicyBundleRecord(self.blob,self.digest)
        self.assertEqual(register_policy_bundles(PolicyEvidenceRegistry(),(record,),max_total_bytes=1).status,'POLICY_TOTAL_BYTE_LIMIT')
    def test_registry_invalid(self):
        record=PolicyBundleRecord(self.blob,self.digest)
        self.assertEqual(register_policy_bundles(PolicyEvidenceRegistry(('bad',)),(record,)).status,'INVALID_POLICY_REGISTRY')

if __name__=='__main__': unittest.main()
