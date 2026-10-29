import json
import unittest
from test_f3_int96_policy_import_witness import policy_witness_fixture
from tools.f3_int89_import_witness_codec import assess_encoded_import
from tools.f3_int97_policy_witness_codec import encode_policy_witness,decode_policy_witness,assess_encoded_policy,safe_to_promote


class PolicyCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.witness=policy_witness_fixture(); cls.catalog=tuple(b[0].record for b in cls.witness.batches)
        cls.blob=encode_policy_witness(cls.witness)
    def mutate(self,edit):
        p=json.loads(self.blob); edit(p); return json.dumps(p).encode()
    def rejected(self,blob,catalog=None):
        self.assertEqual(assess_encoded_policy(blob,self.catalog if catalog is None else catalog).status,'ENCODED_POLICY_WITNESS_REJECTED')
    def test_large_policy_roundtrip(self): self.assertEqual(decode_policy_witness(self.blob,self.catalog),self.witness)
    def test_canonical_roundtrip(self): self.assertEqual(encode_policy_witness(decode_policy_witness(self.blob,self.catalog)),self.blob)
    def test_old_codec_rejects_new_schema(self):
        self.assertEqual(assess_encoded_import(self.blob,self.catalog).status,'ENCODED_IMPORT_WITNESS_REJECTED')
    def test_wrong_schema(self): self.rejected(self.mutate(lambda p:p.update(schema=1)))
    def test_policy_downgrade_tampering(self): self.rejected(self.mutate(lambda p:p['initial']['policy'].update(max_files=512)))
    def test_bool_policy(self): self.rejected(self.mutate(lambda p:p['initial']['policy'].update(max_files=True)))
    def test_excessive_policy(self): self.rejected(self.mutate(lambda p:p['initial']['policy'].update(max_files=2049)))
    def test_unknown_policy_field(self): self.rejected(self.mutate(lambda p:p['initial']['policy'].update(authorized=True)))
    def test_catalog_missing(self): self.rejected(self.blob,self.catalog[:1])
    def test_catalog_duplicate(self): self.rejected(self.blob,self.catalog+self.catalog[:1])
    def test_trace_digest_tampering(self): self.rejected(self.mutate(lambda p:p.update(left_trace_sha256='0'*64)))
    def test_duplicate_json_key(self): self.rejected(b'{"schema":0,'+self.blob[1:])
    def test_flags(self):
        r=assess_encoded_policy(self.blob,self.catalog); self.assertEqual(r.classification,'ORDER_ONLY'); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
