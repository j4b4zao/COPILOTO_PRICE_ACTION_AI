"""A14.3: bounded delay / injected pre-cleanup failure in isolated outer Job.

Windows only. The real Peer.close implementation is never modified on disk.
Every path invokes the real cleanup in finally, including failed assertions.
"""
import json
import os
from pathlib import Path
import sys
import time
import unittest

import test_f3_int121_a12_boundaries as a12

if os.name == 'nt':
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools.f3_int115_process_identity import ProcessRef
    from f3_int121_a12_boundaries import _launcher
    from f3_int121_a5_sqlite import canonical
    from f3_int121_a11_native import _wire, _seed
    import test_f3_int121_a11_native as a11_tests
    from test_f3_int121_a6_adapter import CLIENT, WITNESS


@unittest.skipUnless(os.name == 'nt', 'Windows Job Object required')
class OuterCleanupFaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a12.BoundaryTests.setUpClass()

    def _exercise(self, label, inject_failure):
        fixture = a12.BoundaryTests('test_death_before_source_commit')
        outer = None
        refs = []
        cleanup_confirmed = False
        try:
            fixture.setUp()
            payload = dict(root=str(fixture.root), phase='source:before_consumption_commit',
                           config=a11_tests.config(), request=fixture.consume_request(),
                           client_seed=_seed(CLIENT), witness_seed=_seed(WITNESS))
            outer = control.Peer([sys.executable, '-B', '-c',
                _launcher('f3_int121_a13_counterproof', '--negative-supervisor')],
                cwd=Path(__file__).resolve().parent, timeout=45)
            outer.send(canonical(_wire(payload)).decode('utf-8'))
            outer.process.stdin.close()
            boundary = fixture.wait_json(fixture.root / 'boundary.json')
            owner = fixture.wait_json(fixture.root / 'controller.json')
            bridge = fixture.wait_json(fixture.root / 'bridge.json')
            self.assertEqual(boundary['phase'], 'source:before_consumption_commit')
            for role, pid in [('owner', owner['owner_pid']), ('gate', owner['gate_pid']),
                              ('bridge', bridge['bridge_pid']), ('worker', boundary['worker_pid'])]:
                ref = ProcessRef(pid, outer.job.handle)
                refs.append((role, ref))
                self.assertFalse(ref.signalled(), role)
            a11_tests.NativeTests.terminate_pinned_owner(self, refs[0][1])
            outer.process.wait(timeout=8)
            before = {role: ref.signalled() for role, ref in refs}
            self.assertTrue(before['owner'])
            self.assertTrue(any(not before[role] for role in ('gate', 'bridge', 'worker')))

            # The outer safety Job remains alive while cleanup is delayed.
            # This is a deliberately bounded delay, NOT an actual OS failure.
            time.sleep(0.35)
            delayed = {role: ref.signalled() for role, ref in refs}
            self.assertTrue(any(not delayed[role] for role in ('gate', 'bridge', 'worker')),
                            'No surviving descendant to exercise delayed cleanup')

            if inject_failure:
                # Inject failure at the test orchestration boundary, before
                # Peer.close; do not corrupt its implementation or Job handle.
                def attempted_cleanup():
                    raise RuntimeError('A14_3_INJECTED_PRE_CLEANUP_FAILURE')
                with self.assertRaisesRegex(RuntimeError, 'A14_3_INJECTED_PRE_CLEANUP_FAILURE'):
                    attempted_cleanup()
                self.assertFalse(outer.closed)
                self.assertTrue(any(not ref.signalled() for _, ref in refs[1:]))

            # Close in finally as well: any assertion failure still cleans up.
            outer.close()
            cleanup_confirmed = bool(outer.cleanup['confirmed'])
            self.assertTrue(cleanup_confirmed)
            self.assertTrue(all(ref.signalled() for _, ref in refs))
            self.assertEqual(outer.cleanup['active_processes'], 0)
            self.assertFalse(outer.cleanup['live_io_threads'])
            self.assertTrue(all(row['exit_confirmed'] for row in outer.cleanup['processes']))
            print('A14_3_CLEANUP_EVIDENCE=' + json.dumps(dict(
                label=label, optimization=sys.flags.optimize,
                mode='injected_pre_cleanup_failure' if inject_failure else 'bounded_cleanup_delay',
                delay_seconds=0.35, survivor_detected_during_delay=True,
                cleanup_confirmed=cleanup_confirmed,
                all_pinned_handles_signalled=True,
                active_processes_after_cleanup=0,
                runtime_modified=False, real_operations_authorized=False), sort_keys=True), flush=True)
        finally:
            if outer is not None and not outer.closed:
                outer.close()
            for _, ref in refs:
                ref.close()
            fixture.doCleanups()

    def test_bounded_outer_cleanup_delay(self):
        self._exercise('a14_3_bounded_delay', False)

    def test_injected_pre_cleanup_failure_recovered(self):
        self._exercise('a14_3_injected_failure', True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
