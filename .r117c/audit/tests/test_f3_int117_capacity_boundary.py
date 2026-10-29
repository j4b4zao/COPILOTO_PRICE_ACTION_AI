"""Fresh boundary fixtures, parity with 109 and connection-local SQL observation."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import test_f3_int109_offline_consumption_store as prior
from tools import f3_int109_offline_consumption_store as store
from tools import f3_int117_sqlite_write_faults as probe
from tools.f3_int115_multiprocess_recovery import observe_recovery


class SQLObserver:
    def __init__(self):
        self.connections = 0
        self.statements = []
        self.updates_authorized = 0
        self.commits_authorized = 0

    def attach(self, connection):
        self.connections += 1
        connection.set_trace_callback(self.trace)
        connection.set_authorizer(self.authorize)

    def trace(self, statement):
        if statement.lstrip().upper().startswith('UPDATE STATE '):
            statement = 'UPDATE state SET payload=<BLOB> WHERE id=1'
        self.statements.append(statement)

    def authorize(self, action, first, second, database, source):
        if action == sqlite3.SQLITE_UPDATE and first == 'state':
            self.updates_authorized += 1
        if action == sqlite3.SQLITE_TRANSACTION and first == 'COMMIT':
            self.commits_authorized += 1
        return sqlite3.SQLITE_OK


class CapacityBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ConsumptionStoreTests.setUpClass()
        cls.source = prior.ConsumptionStoreTests

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='f117b_')
        self.root = Path(self.temp.name)
        self.path = self.root / 'probe.sqlite'
        self.original = self.root / 'original.sqlite'
        self.observer = SQLObserver()
        self.addCleanup(self.remove_fixture)

    def remove_fixture(self):
        self.temp.cleanup()
        self.assertFalse(self.root.exists())

    def fixture(self, count, *, floor=5000, include_digest=False):
        self.batches = (replace(self.source.next_batches[0], revision=5000),)
        self.chain = probe.build_typed_chain(self.source.segments, **self.source.scope, batches=self.batches)
        self.assertEqual(self.chain.status, 'CHAIN_FIXTURE_UNAUTHENTICATED')
        history = [format(i, '064x') for i in range(count)]
        if include_digest:
            history[-1] = self.chain.digest
        self.before = dict(version=1, generation=count, next_revision=floor,
                           scope=list(self.source.scope.values()), consumed=sorted(history))
        probe.seed(self.path, self.before, 512)
        shutil.copy2(self.path, self.original)
        self.assertEqual(probe.snapshot(self.path)[0], self.before)
        self.prepare_transition(self.before, self.batches)
        self.initial_hash = self.digest(self.path)

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def prepare_transition(self, before, batches):
        chain = probe.build_typed_chain(self.source.segments, **self.source.scope, batches=batches)
        self.after = dict(before, generation=before['generation'] + 1,
            next_revision=batches[-1].revision + 1, consumed=sorted(before['consumed'] + [chain.digest]))
        self.pins = dict(before_state_digest=store._digest(before), after_state_digest=store._digest(self.after),
                        expected_chain_digest=chain.digest, **self.source.scope)
        self.reference = self.root / 'retained.json'
        self.reference.write_text(json.dumps(self.pins, sort_keys=True), encoding='ascii')
        self.retained = self.reference.read_bytes()

    def attempt(self, *, before=None, batches=None, pins=None, scope=None, after=None):
        return probe.write_once(self.path, 'normal', before=self.before if before is None else before,
            after=self.after if after is None else after, pins=self.pins if pins is None else pins,
            segments=self.source.segments, batches=self.batches if batches is None else batches,
            scope=self.source.scope if scope is None else scope, connection_observer=self.observer.attach)

    def compare_original(self, *, pins=None, scope=None):
        pins = self.pins if pins is None else pins
        return store.consume_chain(self.original, self.source.segments,
            expected_state_digest=pins['before_state_digest'], expected_digest=pins['expected_chain_digest'],
            batches=self.batches, **(self.source.scope if scope is None else scope))

    def unchanged(self, attempt, status):
        self.assertEqual(attempt['status'], status)
        self.assertFalse(attempt['committed'])
        self.assertIsNone(attempt['error'])
        self.assertNotIn('update_entered', attempt['events'])
        self.assertNotIn('commit_entered', attempt['events'])
        self.assertEqual(attempt['events'][-1], 'connection_closed')
        self.assertEqual(self.observer.updates_authorized, 0)
        self.assertEqual(self.observer.commits_authorized, 0)
        self.assertEqual(self.digest(self.path), self.initial_hash)
        self.assertEqual(probe.snapshot(self.path)[0], self.before)
        self.assertEqual(self.reference.read_bytes(), self.retained)

    def test_4095_accepts_4096_parity_and_reopen(self):
        self.fixture(4095)
        attempt = self.attempt()
        original = self.compare_original()
        self.assertEqual(attempt['status'], original.status)
        self.assertEqual(attempt['status'], 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertTrue(attempt['committed'])
        state = probe.snapshot(self.path)[0]
        self.assertEqual(state, self.after)
        self.assertEqual(state, probe.snapshot(self.original)[0])
        self.assertEqual(len(state['consumed']), 4096)
        self.assertEqual(self.observer.updates_authorized, 1)
        self.assertEqual(self.observer.commits_authorized, 1)
        print(json.dumps(dict(boundary=4095, accepted=4096, attempt=attempt, observer=vars(self.observer))), flush=True)

    def test_4096_rejects_4097_before_sql_writes(self):
        self.fixture(4096)
        attempt = self.attempt()
        self.assertEqual(self.compare_original().status, 'HISTORY_CAPACITY_EXHAUSTED')
        self.unchanged(attempt, 'HISTORY_CAPACITY_EXHAUSTED')
        self.assertEqual(attempt['events'][-4:-1], ['chain_verified', 'capacity_checked',
                                                  'admission_rejected:HISTORY_CAPACITY_EXHAUSTED'])
        self.assertEqual(probe.snapshot(self.original)[0], self.before)
        print(json.dumps(dict(boundary=4096, rejected=4097, attempt=attempt, observer=vars(self.observer))), flush=True)

    def test_same_fixture_fill_then_reject_next_operation(self):
        self.fixture(4095)
        self.assertTrue(self.attempt()['committed'])
        full = probe.snapshot(self.path)[0]
        self.before = full
        self.batches = (replace(self.batches[0], revision=5001),)
        self.prepare_transition(full, self.batches)
        self.initial_hash = self.digest(self.path)
        self.observer = SQLObserver()
        self.unchanged(self.attempt(), 'HISTORY_CAPACITY_EXHAUSTED')
        self.assertEqual(len(probe.snapshot(self.path)[0]['consumed']), 4096)

    def test_validation_order_anchor_precedes_capacity(self):
        self.fixture(4096)
        pins = dict(self.pins, before_state_digest='f' * 64)
        self.assertEqual(self.compare_original(pins=pins).status, 'STATE_ANCHOR_MISMATCH')
        self.unchanged(self.attempt(pins=pins), 'STATE_ANCHOR_MISMATCH')

    def test_validation_order_scope_precedes_capacity(self):
        self.fixture(4096)
        scope = dict(self.source.scope, run_id='different')
        self.assertEqual(self.compare_original(scope=scope).status, 'STORE_SCOPE_MISMATCH')
        self.unchanged(self.attempt(scope=scope), 'STORE_SCOPE_MISMATCH')

    def test_validation_order_chain_precedes_capacity(self):
        self.fixture(4096)
        pins = dict(self.pins, expected_chain_digest='0' * 64)
        self.assertEqual(self.compare_original(pins=pins).status, 'CHAIN_DIGEST_MISMATCH')
        self.unchanged(self.attempt(pins=pins), 'CHAIN_DIGEST_MISMATCH')

    def test_revision_domain_precedes_chain_and_capacity(self):
        self.fixture(4096, floor=2147483648)
        self.assertEqual(self.compare_original().status, 'REVISION_DOMAIN_EXHAUSTED')
        self.unchanged(self.attempt(), 'REVISION_DOMAIN_EXHAUSTED')

    def test_history_replay_barrier_without_stale_revision(self):
        # Synthetic isolation fixture: floor permits this revision; the digest
        # already present must be the barrier, before capacity is considered.
        self.fixture(4096, include_digest=True)
        self.assertEqual(self.before['next_revision'], self.batches[0].revision)
        self.assertEqual(self.compare_original().status, 'CHAIN_ALREADY_CONSUMED')
        self.unchanged(self.attempt(), 'CHAIN_ALREADY_CONSUMED')

    def test_reconciliation_from_retained_file_and_actual_anchor_replay(self):
        self.fixture(4095)
        old_pins = json.loads(self.reference.read_bytes())
        self.assertTrue(self.attempt()['committed'])
        full = probe.snapshot(self.path)[0]
        committed = observe_recovery(self.path, **old_pins)
        self.assertEqual(committed.status, 'COMMITTED_OBSERVED_UNAUTHENTICATED')
        for anchor, status in ((old_pins['before_state_digest'], 'STATE_ANCHOR_MISMATCH'),
                               (old_pins['after_state_digest'], 'STALE_CHAIN_REVISION')):
            result = store.consume_chain(self.path, self.source.segments, expected_state_digest=anchor,
                expected_digest=old_pins['expected_chain_digest'], batches=self.batches, **self.source.scope)
            self.assertEqual(result.status, status)
        self.before = full
        self.batches = (replace(self.batches[0], revision=5001),)
        self.prepare_transition(full, self.batches)
        self.initial_hash = self.digest(self.path)
        self.observer = SQLObserver()
        self.unchanged(self.attempt(), 'HISTORY_CAPACITY_EXHAUSTED')
        retained = json.loads(self.reference.read_bytes())
        observed = observe_recovery(self.path, **retained)
        self.assertEqual(observed.status, 'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')
        self.assertFalse(observed.retry_allowed)
        self.assertEqual(probe.snapshot(self.path)[0], full)
        self.assertEqual(self.reference.read_bytes(), self.retained)

    def native_counter(self, mode, code):
        calls = []
        observer = SQLObserver()

        def counted_writer(path, actual_mode, **arguments):
            calls.append((str(path), actual_mode))
            return probe.write_once(path, actual_mode, connection_observer=observer.attach, **arguments)

        result = probe.run_experiment(mode, segments=self.source.segments,
            previous_batches=self.source.batches, batches=self.source.next_batches,
            scope=self.source.scope, writer=counted_writer)
        self.assertEqual(len(calls), 1)
        self.assertEqual(observer.connections, 1)
        self.assertEqual(observer.updates_authorized, 1)
        self.assertEqual(observer.commits_authorized, 0)
        self.assertEqual(result['attempt']['error']['primary_code'], code)
        self.assertEqual(result['attempt']['error']['phase'], 'UPDATE')
        self.assertTrue(result['database_unchanged_on_failure'])
        self.assertTrue(result['fixture_removed'])
        self.assertFalse(result['retry_allowed'])
        print(json.dumps(dict(independent_native=mode, writer_calls=len(calls),
            observer=vars(observer), attempt=result['attempt'])), flush=True)

    def test_full_fresh_fixture_independent_attempt_counter(self):
        self.native_counter('full', sqlite3.SQLITE_FULL)

    def test_readonly_fresh_fixture_independent_attempt_counter(self):
        self.native_counter('readonly', sqlite3.SQLITE_READONLY)

    def test_boundaries_and_order_under_optimization(self):
        names = ('test_4095_accepts_4096_parity_and_reopen', 'test_4096_rejects_4097_before_sql_writes',
            'test_same_fixture_fill_then_reject_next_operation', 'test_validation_order_chain_precedes_capacity',
            'test_history_replay_barrier_without_stale_revision',
            'test_reconciliation_from_retained_file_and_actual_anchor_replay')
        prefix = 'test_f3_int117_capacity_boundary.CapacityBoundaryTests.'
        # The -c check makes optimization itself a prerequisite, not a flag
        # inferred only from the command metadata.
        script = ('import sys,unittest; '
                  'exec("if __debug__:\\n raise RuntimeError(\'Expected optimization\')"); '
                  'unittest.main(module=None,argv=["boundary-O"]+sys.argv[1:],verbosity=2)')
        result = subprocess.run([sys.executable, '-O', '-B', '-c', script, *[prefix+n for n in names]],
            cwd=ROOT/'tests', capture_output=True, text=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Ran 6 tests', result.stderr)
        print(json.dumps(dict(boundary_optimized=True, tests=6, exit_code=result.returncode,
                              child_stdout=result.stdout, child_stderr=result.stderr)), flush=True)

    def test_invalid_helper_modes_rejected_before_connection(self):
        with self.assertRaises(probe.ProbeError):
            probe.write_once(self.path, 'unsupported', before={}, after={}, pins={},
                             segments=(), batches=(), scope={}, connection_observer=self.observer.attach)
        with self.assertRaises(probe.ProbeError):
            probe.validate_attempt('unsupported', {})
        self.assertEqual(self.observer.connections, 0)
        self.assertFalse(self.path.exists())

    def test_bad_after_transition_rejected_without_writes(self):
        self.fixture(4095)
        with self.assertRaises(probe.ProbeError):
            self.attempt(after=dict(self.after, generation=999))
        self.assertEqual(self.observer.updates_authorized, 0)
        self.assertEqual(self.observer.commits_authorized, 0)
        self.assertEqual(self.digest(self.path), self.initial_hash)
        self.assertEqual(probe.snapshot(self.path)[0], self.before)


if __name__ == '__main__':
    unittest.main()
