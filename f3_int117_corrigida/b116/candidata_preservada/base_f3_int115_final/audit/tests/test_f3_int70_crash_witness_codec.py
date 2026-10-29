import json
import unittest
from test_f3_int53_interleaving import recovery
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int68_crash_witness_simulator import find_crash_witness
from tools.f3_int69_crash_minimizer_simulator import minimize_crash_witness
from tools.f3_int70_crash_witness_codec import encode_witness, decode_witness, assess_encoded, safe_to_promote, MAX_BYTES


class CodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requests=(request('a',**recovery(6)),request('b',**recovery(5)))
        cls.witness=minimize_crash_witness(find_crash_witness(requests).witness).witness
        cls.blob=encode_witness(cls.witness)
    def mutate(self,change):
        payload=json.loads(self.blob); change(payload)
        return json.dumps(payload).encode()
    def rejected(self,blob): self.assertEqual(assess_encoded(blob).status,'ENCODED_CRASH_WITNESS_REJECTED')
    def test_roundtrip(self): self.assertEqual(decode_witness(self.blob),self.witness)
    def test_canonical_roundtrip(self): self.assertEqual(encode_witness(decode_witness(self.blob)),self.blob)
    def test_unknown_schema(self): self.rejected(self.mutate(lambda p:p.update(schema=2)))
    def test_bool_schema(self): self.rejected(self.mutate(lambda p:p.update(schema=True)))
    def test_unknown_top_level_field(self): self.rejected(self.mutate(lambda p:p.update(__class__='os.system')))
    def test_duplicate_json_key(self): self.rejected(b'{"schema":0,'+self.blob[1:])
    def test_duplicate_argument(self):
        self.rejected(self.mutate(lambda p:p['requests'][0]['arguments'].append(p['requests'][0]['arguments'][0])))
    def test_unknown_tag(self):
        self.rejected(self.mutate(lambda p:p['requests'][0]['arguments'][0][1].update(kind='arbitrary_class')))
    def test_digest_tampering(self): self.rejected(self.mutate(lambda p:p.update(left_sha256='0'*64)))
    def test_event_tampering(self): self.rejected(self.mutate(lambda p:p['left_events'][0].__setitem__(0,'unknown')))
    def test_request_tampering(self): self.rejected(self.mutate(lambda p:p['requests'][0].update(round_id='forged')))
    def test_nonfinite_json(self): self.rejected(self.blob.replace(b'"schema":1',b'"schema":NaN'))
    def test_oversized_bytes(self): self.rejected(b' '* (MAX_BYTES+1))
    def test_wrong_input_type(self): self.rejected(self.blob.decode())
    def test_unknown_argument_field(self):
        self.rejected(self.mutate(lambda p:p['requests'][0]['arguments'].append(['unknown',None])))
    def test_deep_json(self): self.rejected(b'['*40+b'0'+b']'*40)
    def test_invalid_encoder_input(self):
        with self.assertRaises(ValueError): encode_witness(None)
    def test_flags(self):
        r=assess_encoded(self.blob); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
