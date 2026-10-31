from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_f3_int121_a10_worker import WorkerTests as FixtureHarness
from test_f3_int121_a6_adapter import CLIENT, WITNESS, TRUST, STORE, SCOPE
from f3_int121_a5_sqlite import SQLiteWitness, public_bytes
from f3_int121_a9_route import RouteConfig, OfflineConsumptionRoute, observe
from f3_int121_a10_worker import WorkRequest, LOCKS
from f3_int121_a11_native import run_native_worker, _wire, _unwire, safe_to_promote

if os.name == 'nt':
    import ctypes
    from ctypes import wintypes as W
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools import f3_int115_process_identity as identity
    from a11_native.tools.f3_int115_process_identity import ProcessRef


def config():
    return RouteConfig(STORE, tuple(SCOPE.values()), public_bytes(CLIENT), public_bytes(WITNESS))


def supervisor_specimen(root, marker, before_assignment=False):
    with (root / 'supervisor-owner.json').open('x') as stream:
        json.dump({'pid': os.getpid()}, stream)
    pins = json.loads((root / 'pins.json').read_text())
    if before_assignment:
        def die_before_assign(job, process):
            with marker.open('x') as stream:
                json.dump({'gate_pid': process.pid}, stream)
            deadline = time.monotonic() + 15
            while not (root / 'release').exists():
                if time.monotonic() > deadline:
                    raise TimeoutError('Observer did not release specimen')
                time.sleep(0.01)
            os._exit(75)
        control.Job.assign = die_before_assign
    run_native_worker(root / 'route.sqlite', config=config(),
        request=WorkRequest('supervisor-specimen', 'inquire', pins),
        timeout_seconds=30, native_timeout_seconds=40,
        _test_mode='hold_tree', _marker_path=root / 'target-marker.json' if before_assignment else marker)


@unittest.skipUnless(os.name == 'nt', 'Real Windows Job Objects required; no permissive substitute')
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FixtureHarness.setUpClass()
        cls.segments, cls.chains = FixtureHarness.segments, FixtureHarness.chains
        cls.before, cls.after = FixtureHarness.before, FixtureHarness.after

    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='a11_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'route.sqlite'
        self.wpath = self.root / 'witness.sqlite'
        self.route = OfflineConsumptionRoute(self.path, config=config(), client_private=CLIENT)
        self.assertEqual(self.route.create_new().state_digest, self.before)
        self.w = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST, create=True)
        self.addCleanup(self.w.close)
        (self.root / 'pins.json').write_text(json.dumps(self.pins()))

    def pins(self):
        return dict(before_state_digest=self.before, after_state_digest=self.after,
                    expected_chain_digest=self.chains[1][1])

    def consume_request(self):
        batches, pin = self.chains[1]
        return WorkRequest('native-consume', 'consume', dict(SCOPE, segments=self.segments,
                           batches=batches, expected_state_digest=self.before, expected_digest=pin))

    def call(self, request, **changes):
        args = dict(config=config(), request=request, timeout_seconds=20, native_timeout_seconds=35)
        if request.operation != 'inquire':
            args['client_private'] = CLIENT
        if request.operation == 'resume':
            args.update(witness_path=self.wpath, witness_private=WITNESS)
        args.update(changes)
        return run_native_worker(self.path, **args)

    def clean(self, result, minimum=2):
        self.assertTrue(result.cleanup_confirmed, asdict(result))
        self.assertTrue(result.assigned_before_target)
        self.assertEqual(result.native_cleanup['active_processes'], 0)
        self.assertEqual(result.native_cleanup['live_io_threads'], [])
        proofs = result.native_cleanup['processes']
        self.assertGreaterEqual(len(proofs), minimum)
        self.assertTrue(all(p['exit_confirmed'] for p in proofs))
        self.assertTrue(all(p['proof'] in ('PINNED_HANDLE_SIGNALLED', 'OWN_JOB_EXIT_NOTIFICATION') for p in proofs))

    def test_real_consume_and_resume_run_inside_job_tree(self):
        first = self.call(self.consume_request())
        self.clean(first, 3)
        self.assertEqual(first.status, 'CONTAINED_WORKER_RETURNED')
        self.assertEqual(first.worker_result['operation_status'], 'CONSUMED_PENDING_ATTESTATION_LOCAL')
        resumed = self.call(WorkRequest('native-resume', 'resume', self.pins()))
        self.clean(resumed, 3)
        self.assertEqual(resumed.worker_result['operation_status'], 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(first.worker_result['reply']['envelope_digest'],
                         resumed.worker_result['reply']['envelope_digest'])
        self.assertEqual(self.w.state()['sequence'], 1)

    def test_bridge_optimization_is_explicitly_preserved(self):
        result = self.call(WorkRequest('optimization', 'inquire', self.pins()))
        self.clean(result, 3)
        self.assertEqual(result.bridge_optimization, sys.flags.optimize)

    def test_native_timeout_kills_bridge_and_living_descendant(self):
        marker = self.root / 'tree.json'
        before = self.path.read_bytes()
        result = self.call(WorkRequest('timeout-tree', 'inquire', self.pins()),
                           native_timeout_seconds=6, _test_mode='hold_tree', _marker_path=marker)
        self.assertTrue(marker.exists())
        self.clean(result, 3)
        self.assertEqual(result.status, 'NATIVE_OUTCOME_UNKNOWN')
        self.assertIsNone(result.worker_result)
        self.assertEqual(self.path.read_bytes(), before)

    def test_normal_root_exit_still_terminates_its_descendant(self):
        result = self.call(WorkRequest('root-exit', 'inquire', self.pins()),
                           _test_mode='root_exit_with_descendant', _marker_path=self.root / 'tree.json')
        self.clean(result, 3)
        self.assertEqual(result.status, 'NATIVE_SPECIMEN_COMPLETED')

    def test_killing_native_supervisor_closes_its_job_and_stops_tree(self):
        marker = self.root / 'tree.json'
        outer = self.outer_specimen(marker, False)
        refs = []
        try:
            data = self.wait_marker(marker)
            refs = [ProcessRef(data[name], outer.job.handle)
                    for name in ('gate_pid', 'bridge_pid', 'descendant_pid')]
            self.assertTrue(all(not ref.signalled() for ref in refs))
            owner = self.wait_marker(self.root / 'supervisor-owner.json')
            owner_ref = ProcessRef(owner['pid'], outer.job.handle)
            refs.append(owner_ref)
            # Kill the actual Python owner, not a virtualenv redirector or the
            # outer safety Job. Verify creation time on the termination handle.
            self.terminate_pinned_owner(owner_ref)
            outer.process.wait(timeout=5)
            until = time.monotonic() + 6
            for ref in refs:
                ref.wait_until(until)
                self.assertTrue(ref.signalled())
        finally:
            for ref in refs:
                ref.close()
            outer.close()  # Independent safety containment, after assertions.

    def terminate_pinned_owner(self, ref):
        kernel = identity.K
        kernel.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
        kernel.TerminateProcess.restype = W.BOOL
        handle = identity.check(kernel.OpenProcess(0x100000 | 0x1000 | 0x1, False, ref.identity['pid']))
        try:
            times = [W.FILETIME() for _ in range(4)]
            identity.check(kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]))
            created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            self.assertEqual(created, ref.identity['creation_100ns'])
            self.assertEqual(kernel.GetProcessId(handle), ref.identity['pid'])
            identity.check(kernel.TerminateProcess(handle, 74))
        finally:
            identity.check(kernel.CloseHandle(handle))

    def test_parent_death_before_assignment_leaves_gate_at_eof_no_target(self):
        marker = self.root / 'before-assign.json'
        outer = self.outer_specimen(marker, True)
        ref = None
        try:
            data = self.wait_marker(marker)
            ref = ProcessRef(data['gate_pid'], outer.job.handle)
            self.assertFalse(ref.signalled())
            (self.root / 'release').touch()
            outer.process.wait(timeout=5)
            self.assertEqual(outer.process.returncode, 75)
            ref.wait_until(time.monotonic() + 6)
            self.assertFalse((self.root / 'target-marker.json').exists())
            self.assertEqual(self.path.read_bytes(), self.initial_bytes)
        finally:
            if ref:
                ref.close()
            outer.close()

    def outer_specimen(self, marker, before):
        self.initial_bytes = self.path.read_bytes()
        return control.Peer([sys.executable, '-B', str(Path(__file__).resolve()),
                             '--supervisor-specimen', str(self.root), str(marker),
                             'before' if before else 'after'],
                            cwd=Path(__file__).resolve().parent, timeout=30)

    def wait_marker(self, marker):
        until = time.monotonic() + 15
        while time.monotonic() < until:
            try:
                return json.loads(marker.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(0.02)
        self.fail('Native specimen marker missing')

    def test_assignment_failure_never_releases_target_or_changes_source(self):
        created = []
        original = control.subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs)
            created.append(process)
            return process
        before = self.path.read_bytes()
        with patch.object(control.Job, 'assign', side_effect=OSError('Injected assignment failure')):
            with patch.object(control.subprocess, 'Popen', side_effect=capture):
                result = self.call(self.consume_request())
        self.assertEqual(result.status, 'NATIVE_CLEANUP_NOT_CONFIRMED')
        self.assertFalse(result.assigned_before_target)
        self.assertFalse(result.cleanup_confirmed)  # Constructor proof is not returned.
        self.assertEqual(len(created), 1)
        self.assertIsNotNone(created[0].poll())
        self.assertEqual(self.path.read_bytes(), before)

    def test_abrupt_inner_worker_commit_can_be_explicitly_resumed(self):
        first = self.call(self.consume_request(), _worker_test_mode='exit_after_consume')
        self.clean(first, 3)
        self.assertEqual(first.worker_result['status'], 'WORKER_OUTCOME_UNKNOWN')
        self.assertEqual(observe(self.path, config=config(), expected_state_digest=self.after).status,
                         'PENDING_OBSERVED_LOCAL')
        resumed = self.call(WorkRequest('resume-after-crash', 'resume', self.pins()))
        self.clean(resumed, 3)
        self.assertEqual(resumed.worker_result['operation_status'], 'LOCAL_ATTESTATION_ACKNOWLEDGED')

    def test_typed_wire_roundtrip_does_not_import_arbitrary_types(self):
        job = self.consume_request()
        self.assertEqual(_unwire(json.loads(json.dumps(_wire(job)))), job)
        with self.assertRaises(ValueError):
            _unwire({'kind': 'os.system', 'value': {}})
        with self.assertRaises(ValueError):
            _wire(object())

    def test_invalid_request_never_starts_permissive_fallback(self):
        result = self.call(WorkRequest('invalid', 'inquire', self.pins()), native_timeout_seconds=float('nan'))
        self.assertFalse(result.cleanup_confirmed)
        self.assertFalse(result.assigned_before_target)
        self.assertIsNone(result.gate_pid)
        self.assertEqual(result.status, 'NATIVE_CLEANUP_NOT_CONFIRMED')

    def test_all_operational_locks_remain_false(self):
        result = self.call(WorkRequest('locks', 'inquire', self.pins()))
        self.clean(result, 3)
        self.assertFalse(safe_to_promote(result))
        for name in LOCKS:
            self.assertIs(asdict(result)[name], False)
            self.assertIs(result.worker_result[name], False)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(NativeTests)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--supervisor-specimen']:
        supervisor_specimen(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4] == 'before')
    else:
        unittest.main()
