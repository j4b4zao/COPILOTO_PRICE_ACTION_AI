"""A13: prove A12 detects missing inner Job close-kill, before safety cleanup."""
import json
import os
from pathlib import Path
import sys
import time
import unittest

from f3_int121_a12_boundaries import _launcher
import test_f3_int121_a12_boundaries as a12_tests

if os.name == 'nt':
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools.f3_int115_process_identity import ProcessRef


@unittest.skipUnless(os.name == 'nt', 'Windows Job Object required')
class NegativeContainmentProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a12_tests.BoundaryTests.setUpClass()

    def test_missing_inner_kill_on_close_is_detected_before_outer_cleanup(self):
        # Reuse A12 fixture without inheriting its test suite.
        fixture = a12_tests.BoundaryTests('test_death_before_source_commit')
        fixture.setUp()
        outer = None
        refs = []
        evidence = {}
        try:
            payload = dict(root=str(fixture.root), phase='source:before_consumption_commit',
                           config=__import__('test_f3_int121_a11_native').config(),
                           request=fixture.consume_request(),
                           client_seed=__import__('f3_int121_a11_native')._seed(
                               __import__('test_f3_int121_a6_adapter').CLIENT),
                           witness_seed=__import__('f3_int121_a11_native')._seed(
                               __import__('test_f3_int121_a6_adapter').WITNESS))
            outer = control.Peer([sys.executable, '-B', '-c',
                _launcher('f3_int121_a13_counterproof', '--negative-supervisor')],
                cwd=Path(__file__).resolve().parent, timeout=40)
            outer.send(a12_tests.canonical(a12_tests._wire(payload)).decode('utf-8'))
            outer.process.stdin.close()
            boundary = fixture.wait_json(fixture.root / 'boundary.json')
            owner = fixture.wait_json(fixture.root / 'controller.json')
            bridge = fixture.wait_json(fixture.root / 'bridge.json')
            self.assertEqual(boundary['phase'], 'source:before_consumption_commit')
            identities = [('owner', owner['owner_pid']), ('gate', owner['gate_pid']),
                          ('bridge', bridge['bridge_pid']), ('worker', boundary['worker_pid'])]
            for role, pid in identities:
                ref = ProcessRef(pid, outer.job.handle)
                refs.append((role, ref))
                self.assertFalse(ref.signalled(), role)
            # Only the pinned supervisor is killed. No PID-only cleanup.
            __import__('test_f3_int121_a11_native').NativeTests.terminate_pinned_owner(
                self, refs[0][1])
            outer.process.wait(timeout=8)
            # A12 would require all four signalled before safety cleanup.
            # In this deliberately weakened case, at least one MUST survive.
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if any(not ref.signalled() for _, ref in refs[1:]):
                    break
                time.sleep(0.02)
            observed = {role: ref.signalled() for role, ref in refs}
            self.assertTrue(observed['owner'])
            self.assertTrue(any(not observed[r] for r in ('gate', 'bridge', 'worker')),
                            'Negative control not detected: all descendants already exited')
            evidence = dict(stage='F3-INT-121 A13', optimization=sys.flags.optimize,
                            phase=boundary['phase'], handles_signalled_before_safety=observed,
                            negative_control_detected=True,
                            runtime_modified=False, real_operations_authorized=False)
        finally:
            for _, ref in refs:
                ref.close()
            if outer is not None:
                outer.close()  # unchanged outer safety Job must clean survivors
                self.assertTrue(outer.cleanup['confirmed'])
            fixture.doCleanups()
        if evidence:
            print('A13_NEGATIVE_EVIDENCE=' + json.dumps(evidence, sort_keys=True), flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
