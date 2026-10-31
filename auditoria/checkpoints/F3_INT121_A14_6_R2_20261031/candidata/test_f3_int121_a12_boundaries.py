from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from test_f3_int121_a11_native import NativeTests as FixtureHarness, config
from test_f3_int121_a6_adapter import CLIENT, WITNESS, TRUST, STORE, SCOPE
from f3_int121_a5_sqlite import SQLiteWitness, canonical, digest
from f3_int121_a9_route import OfflineConsumptionRoute, reconcile
from f3_int121_a10_worker import WorkRequest, LOCKS
from f3_int121_a11_native import run_native_worker, _seed, _wire
from f3_int121_a12_boundaries import recover_for_inquiry, _launcher, PHASES, safe_to_promote

if os.name == 'nt':
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools.f3_int115_process_identity import ProcessRef


@unittest.skipUnless(os.name == 'nt', 'Real Windows and retained handles required')
class BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FixtureHarness.setUpClass()
        cls.segments, cls.chains = FixtureHarness.segments, FixtureHarness.chains
        cls.before, cls.after = FixtureHarness.before, FixtureHarness.after
        work = Path(__file__).resolve().parent.parent / 'work'
        work.mkdir(exist_ok=True)
        cls.evidence_dir = Path(tempfile.mkdtemp(prefix=f'a12_evidence_O{sys.flags.optimize}_', dir=work))
        (work / f'A12_EVIDENCE_O{sys.flags.optimize}_INDEX.json').write_bytes(canonical(
            dict(directory=str(cls.evidence_dir), optimization=sys.flags.optimize)))

    def setUp(self):
        work = Path(__file__).resolve().parent.parent / 'work'
        self.temp = tempfile.TemporaryDirectory(dir=work, prefix='a12_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'route.sqlite'
        self.wpath = self.root / 'witness.sqlite'
        self.route = OfflineConsumptionRoute(self.path, config=config(), client_private=CLIENT)
        self.assertEqual(self.route.create_new().state_digest, self.before)
        witness = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST, create=True)
        witness.close()
        # Independent pins exist before any mutation or failing process.
        (self.root / 'pins.json').write_bytes(canonical(self.pins()))

    def pins(self):
        return dict(before_state_digest=self.before, after_state_digest=self.after,
                    expected_chain_digest=self.chains[1][1])

    def consume_request(self):
        batches, pin = self.chains[1]
        return WorkRequest('boundary-consume', 'consume', dict(SCOPE, segments=self.segments,
                           batches=batches, expected_state_digest=self.before, expected_digest=pin))

    def inquiry(self, **changes):
        pins = self.pins()
        pins.update(changes)
        return reconcile(self.path, config=config(), **pins)

    def wait_json(self, path, timeout=20):
        until = time.monotonic() + timeout
        last_error = None
        while time.monotonic() < until:
            try:
                return json.loads(path.read_bytes())
            except (FileNotFoundError, json.JSONDecodeError, PermissionError) as error:
                # Windows can temporarily deny a concurrent marker open.
                # Keep the existing deadline; persistent denial still fails.
                last_error = error
                time.sleep(0.02)
        if isinstance(last_error, PermissionError):
            raise last_error
        self.fail('Controlled boundary marker missing: ' + path.name)

    def witness_sequence(self):
        witness = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST)
        try:
            return witness.state()['sequence']
        finally:
            witness.close()

    def run_boundary(self, phase, *, release=False):
        self.assertIn(phase, PHASES)
        original_envelope = None
        if phase.startswith('witness:') or 'ack_commit' in phase:
            args = dict(self.consume_request().arguments)
            segments = args.pop('segments')
            prepared = self.route.consume_chain(segments, **args)
            self.assertEqual(prepared.status, 'CONSUMED_PENDING_ATTESTATION_LOCAL')
            original_envelope = prepared.envelope
            request = WorkRequest('boundary-resume', 'resume', self.pins())
        else:
            request = self.consume_request()
        payload = dict(root=str(self.root), phase=phase, config=config(), request=request,
                       client_seed=_seed(CLIENT), witness_seed=_seed(WITNESS))
        outer = control.Peer([sys.executable, '-B', '-c',
                              _launcher('f3_int121_a12_boundaries', '--supervisor')],
                             cwd=Path(__file__).resolve().parent, timeout=65)
        refs = []
        proof = []
        all_owned_proofs = []
        active_before_safety = None
        safety_cleanup_started = None
        try:
            outer.send(canonical(_wire(payload)).decode('utf-8'))
            outer.process.stdin.close()
            boundary = self.wait_json(self.root / 'boundary.json')
            owner = self.wait_json(self.root / 'controller.json')
            bridge = self.wait_json(self.root / 'bridge.json')
            self.assertEqual(boundary['phase'], phase)
            self.assertEqual(boundary['optimization'], sys.flags.optimize)
            self.assertEqual(bridge['optimization'], sys.flags.optimize)
            self.assertEqual(json.loads((self.root / 'pins.json').read_bytes()), self.pins())
            if release:
                (self.root / 'release-boundary').touch()
                reply = outer.recv()
                outer.wait()
                self.assertEqual(reply['frame']['worker']['operation_status'],
                                 'CONSUMED_PENDING_ATTESTATION_LOCAL')
                self.assertTrue(reply['cleanup']['confirmed'])
                proof = reply['cleanup']['processes']
            else:
                identities = [('owner', owner['owner_pid']), ('gate', owner['gate_pid']),
                              ('bridge', bridge['bridge_pid']), ('worker', boundary['worker_pid'])]
                for role, pid in identities:
                    ref = ProcessRef(pid, outer.job.handle)
                    self.assertFalse(ref.signalled())
                    refs.append((role, ref))
                # Kill only the actual owner of the inner Job. The outer
                # safety Job stays alive until all retained handles signal.
                FixtureHarness.terminate_pinned_owner(self, refs[0][1])
                outer.process.wait(timeout=6)
                until = time.monotonic() + 8
                for role, ref in refs:
                    ref.wait_until(until)
                    self.assertTrue(ref.signalled())
                    proof.append(dict(role=role, identity=dict(ref.identity),
                                      proof='PINNED_HANDLE_SIGNALLED', exit_confirmed=True,
                                      observed_ns=time.perf_counter_ns()))
                self.assertEqual(len(proof), 4)
                # Cover virtualenv redirectors and any other ordinary owned
                # descendants too, before the safety Job can terminate them.
                all_owned_proofs = outer.job.tracker.confirm(time.monotonic() + 8)
                active_before_safety = outer.job.active()
                self.assertEqual(active_before_safety, 0)
                self.assertTrue(all_owned_proofs)
                self.assertTrue(all(row['exit_confirmed'] for row in all_owned_proofs))
        finally:
            for _, ref in refs:
                ref.close()
            safety_cleanup_started = time.perf_counter_ns()
            outer.close()
        self.assertTrue(outer.cleanup['confirmed'])
        if not release:
            self.assertTrue(all(p['observed_ns'] < safety_cleanup_started for p in proof))
        # Preserve journals in place. Record hashes before explicitly allowing
        # SQLite's own recovery; never delete or substitute crash-side files.
        before_open = {}
        for path in (self.path, self.wpath, Path(str(self.path) + '-journal'), Path(str(self.wpath) + '-journal')):
            if path.exists():
                raw = path.read_bytes()
                before_open[path.name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        opened = recover_for_inquiry(self.path, config=config(), client_private=CLIENT,
                                    before_state_digest=self.before, after_state_digest=self.after)
        self.assertEqual(opened.status, 'LOCAL_OPEN_AND_PIN_MATCH_OBSERVED')
        inquiry = self.inquiry()
        uncommitted = phase in ('source:after_state_write', 'source:after_outbox_insert',
                                'source:before_consumption_commit') and not release
        acknowledged = phase == 'source:after_ack_commit'
        expected = ('NOT_COMMITTED_OBSERVED_LOCAL' if uncommitted else
                    'COMMITTED_ACKNOWLEDGED_OBSERVED_LOCAL' if acknowledged else
                    'COMMITTED_PENDING_OBSERVED_LOCAL')
        self.assertEqual(inquiry.status, expected)
        witness_before = self.witness_sequence()
        expected_witness = 0 if uncommitted or phase.startswith('source:after_') and phase != 'source:after_ack_commit' or phase == 'source:before_consumption_commit' or phase == 'witness:before_commit' else 1
        # Consumption-only phases never contacted the witness, even on release.
        if phase in ('source:after_state_write', 'source:after_outbox_insert',
                     'source:before_consumption_commit', 'source:after_consumption_commit'):
            expected_witness = 0
        self.assertEqual(witness_before, expected_witness)
        if phase == 'source:after_consumption_commit':
            unchanged = self.path.read_bytes()
            self.assertEqual(self.inquiry(after_state_digest='f' * 64).status, 'RECONCILIATION_UNRESOLVED')
            self.assertEqual(self.path.read_bytes(), unchanged)
        job = WorkRequest('explicit-inquiry' if uncommitted else 'explicit-resume',
                          'inquire' if uncommitted else 'resume', self.pins())
        recovered = run_native_worker(self.path, config=config(), request=job,
            client_private=CLIENT, witness_path=self.wpath, witness_private=WITNESS,
            timeout_seconds=20, native_timeout_seconds=35)
        self.assertTrue(recovered.cleanup_confirmed, asdict(recovered))
        self.assertEqual(recovered.status, 'CONTAINED_WORKER_RETURNED')
        expected_operation = ('NOT_COMMITTED_OBSERVED_LOCAL' if uncommitted else
                              'ALREADY_ACKNOWLEDGED_LOCAL' if acknowledged else
                              'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(recovered.worker_result['operation_status'], expected_operation)
        if not uncommitted and not acknowledged:
            expected_envelope = digest(original_envelope) if original_envelope else boundary['envelope_digest']
            self.assertEqual(recovered.worker_result['reply']['envelope_digest'], expected_envelope)
        self.assertEqual(self.witness_sequence(), 0 if uncommitted else 1)
        self.assertFalse(safe_to_promote(opened))
        for name in LOCKS:
            self.assertIs(asdict(inquiry)[name], False)
            self.assertIs(asdict(recovered)[name], False)
        evidence = dict(test=self._testMethodName, phase=phase, release_control=release,
                        optimization=sys.flags.optimize, pins_retained_before_failure=self.pins(),
                        reached_boundary=boundary, process_proofs=proof,
                        all_owned_exit_proofs_before_safety=all_owned_proofs,
                        active_processes_before_safety=active_before_safety,
                        safety_cleanup_started_ns=safety_cleanup_started,
                        safety_cleanup_confirmed=outer.cleanup['confirmed'],
                        files_before_explicit_open=before_open,
                        recovery_open_status=opened.status, inquiry_status=inquiry.status,
                        witness_sequence_before_resume=witness_before,
                        recovery_operation_status=recovered.worker_result['operation_status'],
                        witness_sequence_after_resume=0 if uncommitted else 1,
                        runtime_modified=False, operational_locks=dict.fromkeys(LOCKS, False))
        with (self.evidence_dir / (self._testMethodName + '.json')).open('xb') as output:
            output.write(canonical(evidence))

    def test_death_after_source_update(self):
        self.run_boundary('source:after_state_write')

    def test_death_after_pending_insert(self):
        self.run_boundary('source:after_outbox_insert')

    def test_death_before_source_commit(self):
        self.run_boundary('source:before_consumption_commit')

    def test_death_after_source_commit(self):
        self.run_boundary('source:after_consumption_commit')

    def test_death_before_witness_commit(self):
        self.run_boundary('witness:before_commit')

    def test_death_after_witness_commit(self):
        self.run_boundary('witness:after_commit')

    def test_death_before_local_ack_commit(self):
        self.run_boundary('source:before_ack_commit')

    def test_death_after_local_ack_commit(self):
        self.run_boundary('source:after_ack_commit')

    def test_releasing_boundary_without_death_commits_normally(self):
        self.run_boundary('source:before_consumption_commit', release=True)

    def test_invalid_recovery_pins_do_not_initialize_database(self):
        missing = self.root / 'missing.sqlite'
        result = recover_for_inquiry(missing, config=config(), client_private=CLIENT,
                                    before_state_digest=self.before, after_state_digest=self.before)
        self.assertEqual(result.status, 'INVALID_RECONCILIATION_PIN')
        self.assertFalse(missing.exists())


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(BoundaryTests)


if __name__ == '__main__':
    unittest.main()
