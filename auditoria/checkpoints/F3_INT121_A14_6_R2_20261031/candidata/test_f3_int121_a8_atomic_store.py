from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from test_f3_int121_a6_adapter import AdapterTests as FixtureHarness, CLIENT, WITNESS, TRUST, STORE, SCOPE
from f3_int121_a5_sqlite import SQLiteWitness, IntegrityError, ZERO, canonical, digest, public_bytes
from f3_int121_a6_adapter import FreshQuery, LocalChallengeResponder
from f3_int121_a8_atomic_store import AtomicConsumptionStore, safe_to_promote
from a6_vendor.tools import f3_int109_offline_consumption_store as legacy
from a6_vendor.tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain
from a6_vendor.tools.f3_int106_typed_batch_manifest import TypedBatchEntry


def open_store(root, **changes):
    args = dict(store_id=STORE, scope=tuple(SCOPE.values()), client_private=CLIENT,
                witness_public=public_bytes(WITNESS))
    args.update(changes)
    return AtomicConsumptionStore(root / 'atomic.sqlite', **args)


def command(*args):
    return [sys.executable, '-B'] + (['-O'] if sys.flags.optimize else []) + [
        str(Path(__file__).resolve()), '--worker', *map(str, args)]


def worker():
    root, action, stage, ready, gate = sys.argv[2:]
    root = Path(root)
    def fault(point):
        if point == stage:
            os._exit(73)
    store = open_store(root, timeout=15, _fault=fault)
    if ready != '-':
        Path(ready).touch()
        deadline = time.monotonic() + 20
        while not Path(gate).exists():
            if time.monotonic() > deadline:
                raise TimeoutError('Gate timed out')
            time.sleep(0.01)
    if action == 'consume':
        fixture = FixtureHarness('test_real_project_consumption_matches_a5')
        fixture.setUp()
        try:
            batches = (ChainBatch((TypedBatchEntry('audit', 'a8:1'),), 1),)
            pin = build_typed_chain(fixture.segments, **SCOPE, batches=batches).digest
            result = store.consume(fixture.segments, **SCOPE, batches=batches,
                                   expected_state_digest=json.loads((root / 'anchor.json').read_text()),
                                   expected_digest=pin)
        finally:
            fixture.doCleanups()
    else:
        witness = SQLiteWitness(root / 'witness.sqlite', STORE, WITNESS, TRUST)
        result = store.dispatch(witness.submit)
        witness.close()
    store.close()
    print(result.status)


class AtomicStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = FixtureHarness('test_real_project_consumption_matches_a5')
        fixture.setUp()
        try:
            cls.segments = fixture.segments
        finally:
            fixture.doCleanups()
        cls.chains = {}
        for revision in (1, 2, 4096, 4097):
            batches = (ChainBatch((TypedBatchEntry('audit', f'a8:{revision}'),), revision),)
            result = build_typed_chain(cls.segments, **SCOPE, batches=batches)
            if result.status != 'CHAIN_FIXTURE_UNAUTHENTICATED':
                raise ValueError('Invalid test fixture')
            cls.chains[revision] = batches, result.digest

    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='a8_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.s = open_store(self.root, create=True)
        self.addCleanup(self.s.close)
        self.initial = self.s.state()['state_digest']
        (self.root / 'anchor.json').write_text(json.dumps(self.initial))
        self.w = SQLiteWitness(self.root / 'witness.sqlite', STORE, WITNESS, TRUST, create=True)
        self.addCleanup(self.w.close)

    def consume(self, revision=1, **changes):
        batches, pin = self.chains[revision]
        args = dict(SCOPE, expected_state_digest=self.s.state()['state_digest'],
                    expected_digest=pin, batches=batches)
        args.update(changes)
        return self.s.consume(self.segments, **args)

    def reopen(self):
        self.s.close()
        self.s = open_store(self.root)
        self.addCleanup(self.s.close)

    def test_atomic_commit_and_fresh_a6_verification(self):
        result = self.consume()
        self.assertEqual(result.status, 'CONSUMED_PENDING_ATTESTATION_LOCAL')
        state = self.s.state()
        self.assertEqual(state['generation'], 1)
        self.assertEqual(state['pending'], result.envelope)
        self.assertEqual(result.envelope['request']['state_digest'], state['state_digest'])
        self.assertEqual(self.s.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        query = FreshQuery(expected_store_id=STORE, expected_scope=tuple(SCOPE.values()),
                           witness_public=public_bytes(WITNESS))
        response = LocalChallengeResponder(self.w).answer(query.issue())
        self.assertEqual(query.check(self.s.path, response).status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')

    def test_pending_blocks_next_generation_without_writes(self):
        self.consume()
        before = self.s.path.read_bytes()
        self.assertEqual(self.consume(2).status, 'ATTESTATION_PENDING')
        self.assertEqual(self.s.path.read_bytes(), before)
        self.s.dispatch(self.w.submit)
        self.assertEqual(self.consume(2).status, 'CONSUMED_PENDING_ATTESTATION_LOCAL')
        self.assertEqual(self.s.state()['generation'], 2)

    def test_reopen_preserves_exact_pending_envelope(self):
        env = self.consume().envelope
        self.reopen()
        self.assertEqual(self.s.state()['pending'], env)
        self.assertEqual(self.consume(2).status, 'ATTESTATION_PENDING')

    def test_no_separate_prepare_path(self):
        self.assertEqual(self.s.prepare().status, 'PREPARATION_IS_ATOMIC_WITH_CONSUME')
        self.assertEqual(self.s.state()['generation'], 0)

    def test_invalid_anchor_scope_and_chain_preserve_both_tables(self):
        before = self.s.path.read_bytes()
        for changes, status in [(dict(expected_state_digest=None), 'INVALID_STATE_ANCHOR'),
                                (dict(expected_state_digest='f' * 64), 'STATE_ANCHOR_MISMATCH'),
                                (dict(run_id='run:other'), 'STORE_SCOPE_MISMATCH'),
                                (dict(expected_digest='f' * 64), 'CHAIN_DIGEST_MISMATCH')]:
            self.assertEqual(self.consume(**changes).status, status)
            self.assertEqual(self.s.path.read_bytes(), before)

    def test_replay_after_ack_is_rejected(self):
        self.consume()
        self.s.dispatch(self.w.submit)
        self.assertEqual(self.consume().status, 'STALE_CHAIN_REVISION')
        self.assertEqual(self.s.state()['generation'], 1)

    def test_outbox_insert_error_rolls_back_source_update(self):
        self.s.db.execute("CREATE TRIGGER deny BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assertEqual(self.consume().status, 'STORE_ERROR')
        self.assertEqual(self.s.state()['generation'], 0)
        self.assertIsNone(self.s.state()['pending'])

    def test_state_write_error_leaves_no_envelope(self):
        self.s.db.execute("CREATE TRIGGER deny BEFORE UPDATE ON state BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assertEqual(self.consume().status, 'STORE_ERROR')
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM outbox').fetchone(), (0,))

    def test_readonly_failure_rolls_back_both(self):
        self.s.db.execute('PRAGMA query_only=ON')
        self.assertEqual(self.consume().status, 'STORE_ERROR')
        self.assertEqual(self.s.state()['generation'], 0)

    def test_busy_writer_is_rejected(self):
        other = open_store(self.root, timeout=0.05)
        self.addCleanup(other.close)
        batches, pin = self.chains[1]
        self.s.db.execute('BEGIN IMMEDIATE')
        try:
            result = other.consume(self.segments, **SCOPE, batches=batches,
                                   expected_state_digest=self.initial, expected_digest=pin)
            self.assertEqual(result.status, 'STORE_BUSY')
        finally:
            self.s.db.rollback()

    def test_commit_busy_is_unknown_until_reopened(self):
        self.s.close()
        self.s = open_store(self.root, timeout=0.05)
        self.addCleanup(self.s.close)
        reader = sqlite3.connect(self.s.path, isolation_level=None)
        try:
            reader.execute('BEGIN')
            reader.execute('SELECT payload FROM state').fetchone()
            result = self.consume()
            self.assertEqual(result.status, 'COMMIT_OUTCOME_UNKNOWN')
        finally:
            reader.close()
        self.reopen()
        self.assertEqual(self.s.state()['generation'], 0)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM outbox').fetchone(), (0,))

    def test_process_death_after_state_write_is_fully_rolled_back(self):
        self.crash('consume', 'after_state_write')
        self.assert_uncommitted()

    def test_process_death_after_outbox_insert_is_fully_rolled_back(self):
        self.crash('consume', 'after_outbox_insert')
        self.assert_uncommitted()

    def test_process_death_before_commit_is_fully_rolled_back(self):
        self.crash('consume', 'before_consumption_commit')
        self.assert_uncommitted()

    def assert_uncommitted(self):
        self.reopen()
        self.assertEqual(self.s.state()['generation'], 0)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM outbox').fetchone(), (0,))

    def test_process_death_after_commit_keeps_state_and_envelope(self):
        self.crash('consume', 'after_consumption_commit')
        self.reopen()
        state = self.s.state()
        self.assertEqual(state['generation'], 1)
        self.assertIsNotNone(state['pending'])
        self.assertEqual(state['pending']['request']['state_digest'], state['state_digest'])
        self.assertEqual(self.s.dispatch(self.w.submit).envelope, state['pending'])

    def test_process_death_after_witness_ack_recovers_same_receipt(self):
        env = self.consume().envelope
        self.crash('dispatch', 'after_witness_ack')
        self.reopen()
        self.assertEqual(self.s.state()['pending'], env)
        self.assertEqual(self.w.state()['sequence'], 1)
        self.assertEqual(self.s.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(self.w.state()['sequence'], 1)

    def test_process_death_after_ack_commit_is_already_complete(self):
        self.consume()
        self.crash('dispatch', 'after_ack_commit')
        self.reopen()
        self.assertIsNone(self.s.state()['pending'])
        self.assertEqual(self.s.dispatch(self.w.submit).status, 'NOTHING_TO_DISPATCH')

    def crash(self, action, stage):
        proc = subprocess.run(command(self.root, action, stage, '-', '-'),
                              capture_output=True, text=True, timeout=40)
        self.assertEqual(proc.returncode, 73, proc.stdout + proc.stderr)

    def test_lost_response_and_invalid_ack_keep_new_consumption_blocked(self):
        env = self.consume().envelope
        def lost(value):
            self.w.submit(value)
            raise TimeoutError('Lost durable acknowledgment')
        self.assertEqual(self.s.dispatch(lost).status, 'WITNESS_UNAVAILABLE_OR_UNCERTAIN')
        self.assertEqual(self.s.dispatch(lambda value: ('CONFIRMED', {})).status, 'INVALID_WITNESS_RECEIPT')
        self.assertEqual(self.consume(2).status, 'ATTESTATION_PENDING')
        self.assertEqual(self.s.dispatch(self.w.submit).envelope, env)

    def test_ack_write_failure_preserves_pending(self):
        self.consume()
        self.s.db.execute("CREATE TRIGGER deny BEFORE UPDATE ON outbox BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assertEqual(self.s.dispatch(self.w.submit).status, 'STORE_UNAVAILABLE_OR_ACK_UNCERTAIN')
        self.assertIsNotNone(self.s.state()['pending'])
        self.assertEqual(self.consume(2).status, 'ATTESTATION_PENDING')
        self.s.db.execute('DROP TRIGGER deny')
        self.assertEqual(self.s.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')

    def test_dispatch_excludes_other_source_writer(self):
        self.consume()
        def callback(value):
            other = sqlite3.connect(self.s.path, timeout=0)
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    other.execute('UPDATE state SET payload=payload')
            finally:
                other.close()
            return self.w.submit(value)
        self.assertEqual(self.s.dispatch(callback).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')

    def test_concurrent_processes_only_one_generation_admitted(self):
        gate = self.root / 'gate'
        ready = [self.root / f'ready{i}' for i in range(2)]
        procs = [subprocess.Popen(command(self.root, 'consume', '', ready[i], gate),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for i in range(2)]
        try:
            deadline = time.monotonic() + 20
            while not all(p.exists() for p in ready):
                if time.monotonic() > deadline:
                    self.fail('Workers not ready')
                time.sleep(0.01)
            gate.touch()
            results = []
            for proc in procs:
                stdout, stderr = proc.communicate(timeout=40)
                self.assertEqual(proc.returncode, 0, stderr)
                results.append(stdout.strip())
            self.assertEqual(sorted(results), ['ATTESTATION_PENDING', 'CONSUMED_PENDING_ATTESTATION_LOCAL'])
            self.assertEqual(self.s.state()['generation'], 1)
            self.assertEqual(self.s.db.execute('SELECT count(*) FROM outbox').fetchone(), (1,))
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate()

    def test_legacy_writer_bypass_is_detected_not_claimed_prevented(self):
        batches, pin = self.chains[1]
        result = legacy.consume_chain(self.s.path, self.segments, **SCOPE,
                                      batches=batches, expected_state_digest=self.initial, expected_digest=pin)
        self.assertEqual(result.status, 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        with self.assertRaises(IntegrityError):
            self.s.state()
        with self.assertRaises(IntegrityError):
            open_store(self.root)
        self.assertEqual(self.s.consume(self.segments, **SCOPE, batches=batches,
                                       expected_state_digest=result.state_digest,
                                       expected_digest=pin).status, 'ATTESTATION_STATE_MISMATCH')

    def test_missing_or_existing_database_never_reset(self):
        before = self.s.path.read_bytes()
        with self.assertRaises(FileExistsError):
            open_store(self.root, create=True)
        self.assertEqual(self.s.path.read_bytes(), before)
        self.s.close()
        self.s.path.rename(self.root / 'preserved.sqlite')
        with self.assertRaises(sqlite3.OperationalError):
            open_store(self.root)
        self.assertFalse((self.root / 'atomic.sqlite').exists())

    def test_wrong_key_and_wal_mode_rejected_on_open(self):
        with self.assertRaises(IntegrityError):
            open_store(self.root, witness_public=public_bytes(CLIENT))
        self.s.close()
        conn = sqlite3.connect(self.root / 'atomic.sqlite')
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            with self.assertRaises(IntegrityError):
                open_store(self.root)
        finally:
            conn.close()

    def test_capacity_boundary_preserves_atomic_state_and_outbox(self):
        # Synthetic signed history: no claim that 4095 real consumptions ran.
        state = dict(version=1, generation=4095, next_revision=4096,
                     scope=list(SCOPE.values()), consumed=sorted(
                         hashlib.sha256(f'capacity:{i}'.encode()).hexdigest() for i in range(4095)))
        state_digest = legacy._digest(state)
        head = ZERO
        self.s.db.execute('BEGIN IMMEDIATE')
        for seq in range(1, 4096):
            req = dict(schema='F3-INT-121-A4-LOCAL', store_id=STORE, sequence=seq, generation=seq,
                       state_digest=state_digest if seq == 4095 else hashlib.sha256(str(seq).encode()).hexdigest(),
                       previous_receipt_digest=head, nonce=hashlib.sha256(f'nonce:{seq}'.encode()).hexdigest())
            env = dict(request=req, key_id=self.s.client_id, signature=CLIENT.sign(canonical(req)).hex())
            record = dict(req, schema='F3-INT-121-A4-RECEIPT', request_digest=digest(env))
            receipt = dict(record=record, signature=WITNESS.sign(canonical(record)).hex())
            self.s.db.execute('INSERT INTO outbox VALUES (?, ?, ?)',
                              (seq, canonical(env).decode(), canonical(receipt).decode()))
            head = digest(receipt)
        self.s.db.execute('UPDATE state SET payload=?', (legacy._encode(state),))
        self.s.db.commit()
        self.assertEqual(self.consume(4096).status, 'CONSUMED_PENDING_ATTESTATION_LOCAL')
        def synthetic_witness(env):
            record = dict(env['request'], schema='F3-INT-121-A4-RECEIPT', request_digest=digest(env))
            return 'CONFIRMED', dict(record=record, signature=WITNESS.sign(canonical(record)).hex())
        self.assertEqual(self.s.dispatch(synthetic_witness).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        before = self.s.path.read_bytes()
        self.assertEqual(self.consume(4097).status, 'HISTORY_CAPACITY_EXHAUSTED')
        self.assertEqual(self.s.path.read_bytes(), before)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM outbox').fetchone(), (4096,))

    def test_operational_flags_remain_false(self):
        results = [self.consume(), self.consume(2), self.s.dispatch(self.w.submit)]
        for result in results:
            self.assertFalse(safe_to_promote(result))
            for name in ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
                         'native_prototype_authorized', 'strict_deadline_guaranteed', 'authenticated_witness_verified'):
                self.assertIs(asdict(result)[name], False, name)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(AtomicStoreTests)


if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker()
    else:
        unittest.main()
