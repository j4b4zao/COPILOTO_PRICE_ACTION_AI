import hashlib
from io import BytesIO
import json
import unittest
import zipfile
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot
from tools.f3_int84_import_schedule_divergence import run_import_schedule
from tools.f3_int88_import_divergence_witness import ImportWitness
from tools.f3_int90_import_witness_bundle import encode_import_bundle,decode_import_bundle,assess_import_bundle,safe_to_promote


def fixture_import_witness():
    initial=RegistrySnapshot(); batches=(import_requests('a','b'),import_requests('c','d',1))
    left=run_import_schedule(initial,batches,(('prepare',0),('commit',0),('prepare',1),('commit',1)))
    right=run_import_schedule(initial,batches,(('prepare',1),('commit',1),('prepare',0),('commit',0)))
    return ImportWitness(initial,batches,left,right)


def rewrite_bundle(blob,change):
    with zipfile.ZipFile(BytesIO(blob)) as source: files={n:source.read(n) for n in source.namelist()}
    change(files); stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as target:
        for name,data in files.items(): target.writestr(name,data)
    return stream.getvalue()


class ImportBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.witness=fixture_import_witness(); cls.blob=encode_import_bundle(cls.witness); cls.digest=hashlib.sha256(cls.blob).hexdigest()
    def rejected(self,blob): self.assertEqual(assess_import_bundle(blob,hashlib.sha256(blob).hexdigest()).status,'IMPORT_BUNDLE_REJECTED')
    def test_roundtrip(self): self.assertEqual(decode_import_bundle(self.blob,self.digest),self.witness)
    def test_fixed_metadata_deterministic(self): self.assertEqual(encode_import_bundle(self.witness),self.blob)
    def test_external_digest_tampering(self): self.assertEqual(assess_import_bundle(self.blob,'0'*64).status,'IMPORT_BUNDLE_REJECTED')
    def test_extra_entry(self): self.rejected(rewrite_bundle(self.blob,lambda files:files.update({'extra.txt':b'x'})))
    def test_missing_witness(self): self.rejected(rewrite_bundle(self.blob,lambda files:files.pop('witness.json')))
    def test_witness_payload_tampering(self): self.rejected(rewrite_bundle(self.blob,lambda files:files.update({'witness.json':b'{}'})))
    def test_catalog_payload_tampering(self):
        def change(files):
            name=next(n for n in files if n.startswith('catalog/')); files[name]+=b'x'
        self.rejected(rewrite_bundle(self.blob,change))
    def test_manifest_duplicate_json_keys(self):
        def change(files): files['bundle_manifest.json']=b'{"schema":0,'+files['bundle_manifest.json'][1:]
        self.rejected(rewrite_bundle(self.blob,change))
    def test_manifest_bool_stage(self):
        def change(files):
            p=json.loads(files['bundle_manifest.json']); p['records'][0]['stage']=True; files['bundle_manifest.json']=json.dumps(p).encode()
        self.rejected(rewrite_bundle(self.blob,change))
    def test_manifest_path_escape(self):
        def change(files):
            p=json.loads(files['bundle_manifest.json']); p['records'][0]['file']='../escape.zip'; files['bundle_manifest.json']=json.dumps(p).encode()
        self.rejected(rewrite_bundle(self.blob,change))
    def test_invalid_bytes(self): self.rejected(b'not-a-zip')
    def test_flags(self):
        r=assess_import_bundle(self.blob,self.digest); self.assertEqual(r.classification,'ORDER_ONLY'); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
