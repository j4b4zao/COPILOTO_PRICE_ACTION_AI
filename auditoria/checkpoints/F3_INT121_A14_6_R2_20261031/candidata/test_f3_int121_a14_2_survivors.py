"""A14.2: repeated positive/negative Windows containment observations.

Offline-only regression probes. They reuse the A12 and A13 harness without
importing their TestCase classes into module globals (unittest discovery).
No new fault primitive, no claim of exhaustive scheduling or live readiness.
"""
import contextlib
import io
import json
import os
import sys
import unittest

import test_f3_int121_a12_boundaries as a12
import test_f3_int121_a13_counterproof as a13


@unittest.skipUnless(os.name == 'nt', 'Windows Job Object required')
class SurvivorDetectionRepeatability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a12.BoundaryTests.setUpClass()

    def _negative_repeat(self, label):
        # A13 creates its own fresh isolated SQLite fixtures and outer safety Job.
        test = a13.NegativeContainmentProof(
            'test_missing_inner_kill_on_close_is_detected_before_outer_cleanup')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            test.test_missing_inner_kill_on_close_is_detected_before_outer_cleanup()
        lines = [line.split('=', 1)[1] for line in output.getvalue().splitlines()
                 if line.startswith('A13_NEGATIVE_EVIDENCE=')]
        self.assertEqual(len(lines), 1, output.getvalue())
        proof = json.loads(lines[0])
        self.assertTrue(proof['negative_control_detected'])
        self.assertTrue(proof['handles_signalled_before_safety']['owner'])
        self.assertTrue(any(not proof['handles_signalled_before_safety'][role]
                            for role in ('gate', 'bridge', 'worker')))
        self.assertEqual(proof['optimization'], sys.flags.optimize)
        self.assertFalse(proof['real_operations_authorized'])
        self.assertFalse(proof['runtime_modified'])
        print('A14_2_SURVIVOR_EVIDENCE=' + json.dumps({
            'label': label, 'mode': 'negative_missing_inner_kill_on_close',
            'optimization': sys.flags.optimize,
            'handles_signalled_before_safety': proof['handles_signalled_before_safety'],
            'negative_control_detected': True, 'real_operations_authorized': False,
        }, sort_keys=True), flush=True)

    def test_negative_repeat_first(self):
        self._negative_repeat('a14_2_negative_first')

    def test_negative_repeat_second(self):
        self._negative_repeat('a14_2_negative_second')

    def test_positive_inner_kill_on_close(self):
        # A12's positive control: all pinned descendants must be signalled
        # before the outer safety Job is closed, with independent fixture data.
        fixture = a12.BoundaryTests('test_death_before_source_commit')
        fixture._testMethodName = 'a14_2_positive_inner_kill_on_close'
        try:
            fixture.setUp()
            fixture.run_boundary('source:before_consumption_commit')
            path = fixture.evidence_dir / (fixture._testMethodName + '.json')
            proof = json.loads(path.read_bytes())
            self.assertEqual(proof['active_processes_before_safety'], 0)
            self.assertTrue(proof['safety_cleanup_confirmed'])
            self.assertFalse(proof['runtime_modified'])
            self.assertEqual(proof['optimization'], sys.flags.optimize)
            self.assertTrue(all(value is False for value in
                                proof['operational_locks'].values()))
            print('A14_2_SURVIVOR_EVIDENCE=' + json.dumps({
                'label': 'a14_2_positive_inner_kill_on_close',
                'mode': 'positive_inner_kill_on_close',
                'optimization': sys.flags.optimize,
                'active_processes_before_safety': 0,
                'safety_cleanup_confirmed': True,
                'real_operations_authorized': False,
            }, sort_keys=True), flush=True)
        finally:
            fixture.doCleanups()


if __name__ == '__main__':
    unittest.main(verbosity=2)
