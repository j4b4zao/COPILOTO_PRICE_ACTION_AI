import json
import unittest
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot
from tools.f3_int84_import_schedule_divergence import run_import_schedule
from tools.f3_int88_import_divergence_witness import ImportWitness
from tools.f3_int89_import_witness_codec import encode_import_witness,decode_import_witness,assess_encoded_import,safe_to_promote


class ImportCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial=RegistrySnapshot(); cls.batches=(import_requests('a','b'),import_requests('c','d',1))
        left=run_import_schedule(cls.initial,cls.batches,(('prepare',0),('commit',0),('prepare',1),('commit',1)))
        right=run_import_schedule(cls.initial,cls.batches,(('prepare',1),('commit',1),('prepare',0),('commit',0)))
        cls.witness=ImportWitness(cls.initial,cls.batches,left,right); cls.blob=encode_import_witness(cls.witness)
        cls.catalog=tuple(batch[0].record for batch in cls.batches)
    def mutate(self,change):
        p=json.loads(self.blob); change(p); return json.dumps(p).encode()
    def rejected(self,blob,catalog=None):
        self.assertEqual(assess_encoded_import(blob,self.catalog if catalog is None else catalog).status,'ENCODED_IMPORT_WITNESS_REJECTED')
    def test_roundtrip(self): self.assertEqual(decode_import_witness(self.blob,self.catalog),self.witness)
    def test_canonical_roundtrip(self): self.assertEqual(encode_import_witness(decode_import_witness(self.blob,self.catalog)),self.blob)
    def test_missing_catalog(self): self.rejected(self.blob,self.catalog[:1])
    def test_duplicate_catalog(self): self.rejected(self.blob,self.catalog+self.catalog[:1])
    def test_tampered_catalog_bytes(self):
        r=self.catalog[0]; bad=PackageRecord(r.stage,r.blob+b'x',r.sha256)
        self.rejected(self.blob,(bad,self.catalog[1]))
    def test_reference_stage_mismatch(self): self.rejected(self.mutate(lambda p:p['batches'][0][0].update(stage=999)))
    def test_trace_digest_tampering(self): self.rejected(self.mutate(lambda p:p.update(left_trace_sha256='0'*64)))
    def test_unknown_top_field(self): self.rejected(self.mutate(lambda p:p.update(__class__='arbitrary')))
    def test_bool_schema(self): self.rejected(self.mutate(lambda p:p.update(schema=True)))
    def test_duplicate_json_key(self): self.rejected(b'{"schema":0,'+self.blob[1:])
    def test_initial_version_tampering(self): self.rejected(self.mutate(lambda p:p['initial'].update(version=99)))
    def test_invalid_event_type(self): self.rejected(self.mutate(lambda p:p['left_events'][0].__setitem__(1,False)))
    def test_wrong_input_type(self): self.rejected(self.blob.decode())
    def test_flags(self):
        r=assess_encoded_import(self.blob,self.catalog); self.assertEqual(r.classification,'ORDER_ONLY'); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
