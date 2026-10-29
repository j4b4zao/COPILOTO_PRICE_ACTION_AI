"""F3-INT-13: expanded bounded pure-state exploration; no native interfaces."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).with_name('test_f3_int10_architecture_c_adversarial.py')
spec = importlib.util.spec_from_file_location('f3_int13_base_explorer', SOURCE)
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)
a.MAX_DEPTH = 5
a.MAX_STATES = 150000
a.MAX_TRANSITIONS = 180000
a.MAX_SECONDS = 40.0

class ExpandedAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = a.explore()
        print('F3_INT13_REPORT=' + json.dumps(cls.report, sort_keys=True), flush=True)

    def test_invariants(self):
        self.assertEqual(self.report['safety_violation_occurrences'], 0, self.report['counterexamples'])
        self.assertEqual(self.report['exceptions'], 0, self.report['counterexamples'])

    def test_rejection_contract(self):
        self.assertEqual(self.report['rejection_violation_occurrences'], 0, self.report['counterexamples'])

    def test_accounting(self):
        r = self.report
        self.assertEqual(r['attempted'], r['accepted'] + r['rejected'] + r['no_effect'] + r['exceptions'])
        self.assertGreater(r['attempted'], 36000)
        self.assertGreaterEqual(r['depth_effective'], 2)
        self.assertTrue(all(r['boundary_attempts'][k] > 0 for k in ('before', 'equal', 'after')))
