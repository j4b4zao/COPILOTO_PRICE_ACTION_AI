"""A14.1: repeat A12's controlled supervisor-death boundaries with fresh fixtures.

This is a repeatability check, NOT a new fault-injection primitive, a timing
exhaustiveness claim, or a production authorization. Windows-only, offline.
"""
import json
import os
import sys
import unittest

# Import the module, not its TestCase class, to avoid duplicate discovery.
import test_f3_int121_a12_boundaries as a12


@unittest.skipUnless(os.name == 'nt', 'Windows Job Object required')
class SupervisorDeathPhaseRepeatability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a12.BoundaryTests.setUpClass()

    def _run_fresh(self, phase, label):
        # Every repetition gets its own SQLite files, pins and process tree.
        fixture = a12.BoundaryTests('test_death_before_source_commit')
        fixture._testMethodName = label
        try:
            fixture.setUp()
            fixture.run_boundary(phase)
            path = fixture.evidence_dir / (label + '.json')
            evidence = json.loads(path.read_bytes())
            self.assertEqual(evidence['phase'], phase)
            self.assertEqual(evidence['optimization'], sys.flags.optimize)
            self.assertTrue(evidence['safety_cleanup_confirmed'])
            self.assertEqual(evidence['active_processes_before_safety'], 0)
            self.assertFalse(evidence['runtime_modified'])
            self.assertTrue(all(v is False for v in evidence['operational_locks'].values()))
            print('A14_1_PHASE_EVIDENCE=' + json.dumps({
                'phase': phase, 'label': label,
                'optimization': sys.flags.optimize,
                'active_processes_before_safety': evidence['active_processes_before_safety'],
                'safety_cleanup_confirmed': evidence['safety_cleanup_confirmed'],
                'runtime_modified': False,
                'real_operations_authorized': False,
            }, sort_keys=True), flush=True)
        finally:
            fixture.doCleanups()

    def test_repeat_before_source_commit(self):
        self._run_fresh('source:before_consumption_commit', 'a14_1_before_commit_repeat')

    def test_repeat_after_ack_commit(self):
        self._run_fresh('source:after_ack_commit', 'a14_1_after_ack_repeat')


if __name__ == '__main__':
    unittest.main(verbosity=2)
