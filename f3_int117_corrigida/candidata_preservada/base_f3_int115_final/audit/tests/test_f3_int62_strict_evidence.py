import unittest
from test_f3_int60_package_integrity import fixture
from tools.f3_int62_strict_evidence_simulator import verify_strict_blob, strict_json, safe_to_promote


class StrictEvidenceTests(unittest.TestCase):
    def verify(self,change=None,files_change=None):
        def setup(s):
            s['new_tests']['seconds']=0.1; s['regression']['seconds']=0.2
            if change: change(s)
        blob,digest=fixture(change=setup,files_change=files_change)
        return verify_strict_blob(blob,digest,60)
    def test_valid(self):
        r=self.verify(); self.assertEqual(r.status,'STRICT_EVIDENCE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
    def mutate_json(self,old,new):
        def mutate(files):
            for name in ('CHECKPOINT_F3_INT60.json','ULTIMO_MARCO.json'):
                files[name]=files[name].replace(old,new)
        return self.verify(files_change=mutate)
    def test_duplicate_f3(self):
        r=self.mutate_json(b'"f3": "OPEN"',b'"f3":"CLOSED","f3":"OPEN"')
        self.assertEqual(r.status,'AMBIGUOUS_CHECKPOINT_JSON')
    def test_duplicate_identical_keys(self):
        r=self.mutate_json(b'"tests": 2',b'"tests":2,"tests":2')
        self.assertEqual(r.status,'AMBIGUOUS_CHECKPOINT_JSON')
    def test_nan(self): self.assertEqual(self.mutate_json(b'0.1',b'NaN').status,'AMBIGUOUS_CHECKPOINT_JSON')
    def test_infinity(self): self.assertEqual(self.mutate_json(b'0.1',b'Infinity').status,'AMBIGUOUS_CHECKPOINT_JSON')
    def test_float_overflow(self): self.assertEqual(self.mutate_json(b'0.1',b'1e999').status,'AMBIGUOUS_CHECKPOINT_JSON')
    def test_negative_seconds(self):
        self.assertEqual(self.verify(change=lambda s:s['new_tests'].update(seconds=-1)).status,'INVALID_TEST_DURATION')
    def test_bool_seconds(self):
        self.assertEqual(self.verify(change=lambda s:s['new_tests'].update(seconds=True)).status,'INVALID_TEST_DURATION')
    def test_missing_seconds(self):
        self.assertEqual(self.verify(change=lambda s:s['new_tests'].pop('seconds')).status,'INVALID_TEST_DURATION')
    def test_contradictory_failed_line(self):
        r=self.verify(files_change=lambda f:f.update({'LOG_F3_INT60_NOVOS.txt':b'Ran 2 tests in 0.1s\nFAILED (errors=1)\nOK\n'}))
        self.assertEqual(r.status,'AMBIGUOUS_TEST_LOG')
    def test_duplicate_summary(self):
        r=self.verify(files_change=lambda f:f.update({'LOG_F3_INT60_NOVOS.txt':b'Ran 2 tests in 0.1s\nRan 2 tests in 0.1s\nOK\n'}))
        self.assertEqual(r.status,'AMBIGUOUS_TEST_LOG')
    def test_traceback_despite_ok(self):
        r=self.verify(files_change=lambda f:f.update({'LOG_F3_INT60_NOVOS.txt':b'Traceback (most recent call last):\nRan 2 tests in 0.1s\nOK\n'}))
        self.assertEqual(r.status,'AMBIGUOUS_TEST_LOG')
    def test_duplicate_ok(self):
        r=self.verify(files_change=lambda f:f.update({'LOG_F3_INT60_NOVOS.txt':b'Ran 2 tests in 0.1s\nOK\nOK\n'}))
        self.assertEqual(r.status,'AMBIGUOUS_TEST_LOG')
    def test_strict_json_retains_finite_numbers(self):
        self.assertEqual(strict_json(b'{"x": 1.2, "y": 2}'),{'x':1.2,'y':2})
