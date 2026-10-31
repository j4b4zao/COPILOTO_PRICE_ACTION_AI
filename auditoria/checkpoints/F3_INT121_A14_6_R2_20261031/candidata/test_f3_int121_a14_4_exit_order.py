"""A14.4: controlled process-exit ordering, isolated Windows Job specimens.

No production paths, network trading, or real orders. Every branch performs
outer Job safety cleanup in finally and checks pinned process handles.
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
    import test_f3_int121_a11_native as a11
    from test_f3_int121_a6_adapter import CLIENT, WITNESS


@unittest.skipUnless(os.name == 'nt', 'Windows Job Object required')
class UnexpectedExitOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a12.BoundaryTests.setUpClass()

    def _exercise(self, label, *, negative, order, observational=False):
        fixture = a12.BoundaryTests('test_death_before_source_commit')
        outer = None
        refs = {}
        cleaned = False
        held_fixture = negative and not observational and order in ('worker_first', 'near_simultaneous')
        retention = {}
        try:
            fixture.setUp()
            payload = dict(root=str(fixture.root), phase='source:before_consumption_commit',
                           config=a11.config(), request=fixture.consume_request(),
                           client_seed=_seed(CLIENT), witness_seed=_seed(WITNESS))
            module = 'f3_int121_a13_counterproof' if negative else 'f3_int121_a12_boundaries'
            arguments = ['--negative-supervisor'] if negative else ['--supervisor']
            if held_fixture:
                arguments = ['--negative-supervisor-held']
            outer = control.Peer([sys.executable, '-B', '-c', _launcher(module, *arguments)],
                                 cwd=Path(__file__).resolve().parent, timeout=45)
            outer.send(canonical(_wire(payload)).decode('utf-8'))
            outer.process.stdin.close()
            boundary = fixture.wait_json(fixture.root / 'boundary.json')
            owner = fixture.wait_json(fixture.root / 'controller.json')
            bridge = fixture.wait_json(fixture.root / 'bridge.json')
            self.assertEqual(boundary['phase'], 'source:before_consumption_commit')
            for role, pid in [('owner', owner['owner_pid']), ('gate', owner['gate_pid']),
                              ('bridge', bridge['bridge_pid']), ('worker', boundary['worker_pid'])]:
                refs[role] = ProcessRef(pid, outer.job.handle)
                self.assertFalse(refs[role].signalled(), role)

            def retention_marker(phase):
                marker = fixture.wait_json(fixture.root / ('bridge-retention-' + phase.lower() + '.json'))
                self.assertEqual(marker['schema'], 'A14_6_HELD_BRIDGE')
                self.assertEqual(marker['phase'], phase)
                self.assertEqual(marker['pid'], refs['bridge'].identity['pid'])
                self.assertEqual(marker['specimen_id'], fixture.root.name)
                self.assertEqual(marker['optimization'], sys.flags.optimize)
                self.assertFalse(marker['real_operations_authorized'])
                self.assertFalse(refs['bridge'].signalled())
                retention[phase] = marker
            if held_fixture:
                retention_marker('ARMED')

            kill = lambda role: a11.NativeTests.terminate_pinned_owner(self, refs[role])
            snapshots = {}
            def capture(stage):
                snapshots[stage] = {role: ref.signalled() for role, ref in refs.items()}
            capture('initial')
            if order == 'owner_first':
                kill('owner')
                outer.process.wait(timeout=8)
                deadline = time.monotonic() + 6
                for role, ref in refs.items():
                    ref.wait_until(deadline)
                    self.assertTrue(ref.signalled(), role)
                before = {role: ref.signalled() for role, ref in refs.items()}
                self.assertTrue(all(before.values()))
            elif order == 'worker_first':
                kill('worker')
                capture('after_worker_termination_request')
                refs['worker'].wait_until(time.monotonic() + 6)
                if held_fixture:
                    retention_marker('ACTIVE')
                self.assertFalse(refs['owner'].signalled(), 'Owner exited before explicit owner termination')
                kill('owner')
                capture('after_owner_termination_request')
                outer.process.wait(timeout=8)
                before = {role: ref.signalled() for role, ref in refs.items()}
                self.assertTrue(before['worker'] and before['owner'])
                if not observational:
                    self.assertTrue(any(not before[r] for r in ('gate', 'bridge')),
                                    'Negative control unexpectedly lost all remaining descendants')
            elif order == 'near_simultaneous':
                # Sequential termination requests without an intervening wait:
                # close succession, not proof of truly simultaneous OS exits.
                kill('worker')
                capture('after_worker_termination_request')
                kill('owner')
                capture('after_owner_termination_request')
                outer.process.wait(timeout=8)
                refs['worker'].wait_until(time.monotonic() + 6)
                if held_fixture:
                    retention_marker('ACTIVE')
                before = {role: ref.signalled() for role, ref in refs.items()}
                self.assertTrue(before['owner'] and before['worker'])
                if not observational:
                    self.assertTrue(any(not before[r] for r in ('gate', 'bridge')),
                                    'Negative control unexpectedly lost all remaining descendants')
            else:
                raise ValueError(order)

            capture('before_outer_cleanup')
            if held_fixture:
                self.assertFalse(before['bridge'])
                self.assertFalse((fixture.root / 'release-held-bridge').exists())
            outer.close()
            cleaned = True
            self.assertTrue(outer.cleanup['confirmed'])
            self.assertEqual(outer.cleanup['active_processes'], 0)
            self.assertFalse(outer.cleanup['live_io_threads'])
            self.assertTrue(all(row['exit_confirmed'] for row in outer.cleanup['processes']))
            self.assertTrue(all(ref.signalled() for ref in refs.values()))
            print('A14_4_EXIT_ORDER_EVIDENCE=' + json.dumps(dict(
                label=label, order=order, optimization=sys.flags.optimize,
                negative_control=negative, observational=observational,
                retained_bridge_fixture=held_fixture, bridge_retention=retention,
                identities={role: dict(ref.identity) for role, ref in refs.items()},
                survivor_observed_before_cleanup=any(not before[r] for r in ('gate','bridge')),
                snapshots=snapshots, handles_before_outer_cleanup=before,
                handles_after_outer_cleanup={role: ref.signalled() for role, ref in refs.items()},
                outer_cleanup_confirmed=True, active_processes_after_cleanup=0,
                runtime_modified=False, real_operations_authorized=False,
            ), sort_keys=True), flush=True)
        finally:
            # Safety containment is unconditional, including assertion failures.
            if outer is not None and not outer.closed:
                outer.close()
            for ref in refs.values():
                ref.close()
            fixture.doCleanups()

    def test_supervisor_first_positive_containment(self):
        self._exercise('a14_4_owner_first', negative=False, order='owner_first')

    def test_worker_first_negative_containment(self):
        self._exercise('a14_4_worker_first', negative=True, order='worker_first')

    def test_close_succession_negative_containment(self):
        self._exercise('a14_4_close_succession', negative=True, order='near_simultaneous')


if __name__ == '__main__':
    unittest.main(verbosity=2)
