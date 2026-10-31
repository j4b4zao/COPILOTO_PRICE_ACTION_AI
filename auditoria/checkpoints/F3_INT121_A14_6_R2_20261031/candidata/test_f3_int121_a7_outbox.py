from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from test_f3_int121_a6_adapter import AdapterTests as FixtureHarness, CLIENT, WITNESS, TRUST, STORE, SCOPE
from f3_int121_a5_sqlite import SQLiteWitness, IntegrityError, canonical, public_bytes
from f3_int121_a6_adapter import FreshQuery, LocalChallengeResponder
from f3_int121_a7_outbox import AttestationOutbox, SourceError, safe_to_promote
from a6_vendor.tools import f3_int109_offline_consumption_store as store
from a6_vendor.tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain
from a6_vendor.tools.f3_int106_typed_batch_manifest import TypedBatchEntry


def queue(root, **changes):
    args = dict(store_id=STORE, scope=tuple(SCOPE.values()), client_private=CLIENT,
                witness_public=public_bytes(WITNESS))
    args.update(changes)
    return AttestationOutbox(root / 'outbox.sqlite', root / 'project.sqlite', **args)


def worker():
    root, action, stage = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    def fault(point):
        if point == stage:
            os._exit(73)
    q = queue(root, _fault=fault)
    if action == 'prepare':
        result = q.prepare()
    else:
        w = SQLiteWitness(root / 'witness.sqlite', STORE, WITNESS, TRUST)
        result = q.dispatch(w.submit)
        w.close()
    q.close()
    print(result.status)


class OutboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Produce real project-consumption snapshots once, then clone fixtures.
        fixture = FixtureHarness('test_real_project_consumption_matches_a5')
        fixture.setUp()
        try:
            cls.initial_bytes = fixture.db.read_bytes()
            fixture.consume(1)
            cls.one_bytes = fixture.db.read_bytes()
            fixture.consume(2)
            cls.two_bytes = fixture.db.read_bytes()
            cls.segments = fixture.segments
            cls.capacity_cases = {}
            for count in (4095, 4096):
                batches = (ChainBatch((TypedBatchEntry('audit', 'capacity'),), count + 1),)
                pin = build_typed_chain(cls.segments, **SCOPE, batches=batches).digest
                cls.capacity_cases[count] = (batches, pin)
        finally:
            fixture.doCleanups()

    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='a7_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'project.sqlite'
        self.source.write_bytes(self.initial_bytes)
        self.q = queue(self.root, create=True)
        self.addCleanup(self.q.close)
        self.w = SQLiteWitness(self.root / 'witness.sqlite', STORE, WITNESS, TRUST, create=True)
        self.addCleanup(self.w.close)

    def reopen(self):
        self.q.close()
        self.q = queue(self.root)
        self.addCleanup(self.q.close)

    def first(self):
        self.source.write_bytes(self.one_bytes)
        result = self.q.prepare()
        self.assertEqual(result.status, 'PREPARED_DURABLE_LOCAL')
        return result.envelope

    def test_initial_and_full_flow_matches_fresh_a6_query(self):
        self.assertEqual(self.q.prepare().status, 'NOTHING_TO_ATTEST')
        self.first()
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        q = FreshQuery(expected_store_id=STORE, expected_scope=tuple(SCOPE.values()),
                       witness_public=public_bytes(WITNESS))
        response = LocalChallengeResponder(self.w).answer(q.issue())
        self.assertEqual(q.check(self.source, response).status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')

    def test_reopen_preserves_exact_nonce_and_envelope(self):
        env = self.first()
        self.reopen()
        result = self.q.prepare()
        self.assertEqual(result.status, 'PENDING_ALREADY_DURABLE')
        self.assertEqual(result.envelope, env)

    def test_second_generation_only_after_ack(self):
        self.first()
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(self.q.prepare().status, 'NOTHING_TO_ATTEST')
        self.source.write_bytes(self.two_bytes)
        self.assertEqual(self.q.prepare().status, 'PREPARED_DURABLE_LOCAL')
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(self.w.state()['sequence'], 2)

    def test_generation_gap_never_backfilled(self):
        self.source.write_bytes(self.two_bytes)
        self.assertEqual(self.q.prepare().status, 'SOURCE_GENERATION_GAP_OR_ROLLBACK')
        self.assertEqual(self.w.state()['sequence'], 0)

    def test_advanced_source_bootstrap_rejected(self):
        self.source.write_bytes(self.one_bytes)
        with self.assertRaises(SourceError):
            AttestationOutbox(self.root / 'new.sqlite', self.source,
                              store_id=STORE, scope=tuple(SCOPE.values()),
                              client_private=CLIENT, witness_public=public_bytes(WITNESS), create=True)
        self.assertFalse((self.root / 'new.sqlite').exists())

    def test_unavailable_witness_keeps_pending(self):
        env = self.first()
        self.w.available = False
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'WITNESS_REJECTED')
        self.reopen()
        self.assertEqual(self.q.prepare().envelope, env)
        self.w.available = True
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')

    def test_lost_ack_transport_exception_recovers_exact_receipt(self):
        env = self.first()
        saved = []
        def lost_ack(value):
            result = self.w.submit(value)
            saved.append(result[1])
            raise TimeoutError('Test: response lost after durable commit')
        self.assertEqual(self.q.dispatch(lost_ack).status, 'WITNESS_UNAVAILABLE_OR_UNCERTAIN')
        self.reopen()
        result = self.q.dispatch(self.w.submit)
        self.assertEqual(result.status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(result.envelope, env)
        self.assertEqual(result.receipt, saved[0])
        self.assertEqual(self.w.state()['sequence'], 1)

    def test_invalid_witness_ack_never_saved(self):
        self.first()
        self.assertEqual(self.q.dispatch(lambda env: ('CONFIRMED', {})).status, 'INVALID_WITNESS_RECEIPT')
        self.assertEqual(self.q.prepare().status, 'PENDING_ALREADY_DURABLE')

    def test_transport_mutation_cannot_change_durable_envelope(self):
        env = self.first()
        def mutate(value):
            value['request']['state_digest'] = 'f' * 64
            return 'CONFIRMED', {}
        self.assertEqual(self.q.dispatch(mutate).status, 'INVALID_WITNESS_RECEIPT')
        self.assertEqual(self.q.prepare().envelope, env)

    def test_source_advanced_or_rolled_back_while_pending_rejected(self):
        self.first()
        for raw in (self.two_bytes, self.initial_bytes):
            self.source.write_bytes(raw)
            self.assertEqual(self.q.prepare().status, 'SOURCE_PENDING_MISMATCH')
            self.assertEqual(self.q.dispatch(self.w.submit).status, 'SOURCE_PENDING_MISMATCH')
        self.assertEqual(self.w.state()['sequence'], 0)

    def test_source_digest_change_rejected(self):
        self.first()
        conn = sqlite3.connect(self.source)
        try:
            state = store._load(conn)
            state['next_revision'] += 1
            conn.execute('UPDATE state SET payload=?', (store._encode(state),))
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'SOURCE_PENDING_MISMATCH')

    def test_no_repeated_dispatch_after_ack(self):
        self.first()
        self.q.dispatch(self.w.submit)
        def unexpected(_):
            self.fail('No transport call should be made')
        self.assertEqual(self.q.dispatch(unexpected).status, 'NOTHING_TO_DISPATCH')

    def test_source_reader_excludes_normal_writes_during_dispatch(self):
        self.first()
        def writer(value):
            conn = sqlite3.connect(self.source, timeout=0)
            try:
                conn.execute('UPDATE state SET payload=payload')
                with self.assertRaises(sqlite3.OperationalError):
                    conn.commit()
            finally:
                conn.close()
            return self.w.submit(value)
        self.assertEqual(self.q.dispatch(writer).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')

    def test_tampered_envelope_blocks_prepare_and_dispatch(self):
        self.first()
        self.q.db.execute("UPDATE outbox SET envelope='{}'")
        self.assertEqual(self.q.prepare().status, 'QUEUE_INTEGRITY_ERROR')
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'QUEUE_INTEGRITY_ERROR')

    def test_wrong_pinned_identity_blocks_reopen(self):
        with self.assertRaises(IntegrityError):
            queue(self.root, store_id='OTHER')

    def test_queue_not_recreated_and_source_not_modified(self):
        before = self.source.read_bytes()
        with self.assertRaises(FileExistsError):
            queue(self.root, create=True)
        self.assertEqual(self.source.read_bytes(), before)
        self.q.close()
        self.q.path.rename(self.root / 'preserved.sqlite')
        with self.assertRaises(sqlite3.OperationalError):
            queue(self.root)
        self.assertFalse((self.root / 'outbox.sqlite').exists())

    def test_queue_write_failure_does_not_send(self):
        self.source.write_bytes(self.one_bytes)
        self.q.db.execute("CREATE TRIGGER deny BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assertEqual(self.q.prepare().status, 'QUEUE_STORAGE_UNAVAILABLE')
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'NOTHING_TO_DISPATCH')
        self.assertEqual(self.w.state()['sequence'], 0)

    def test_process_death_before_prepare_commit_rolls_back(self):
        self.source.write_bytes(self.one_bytes)
        self.crash('prepare', 'after_prepare_insert')
        self.reopen()
        self.assertEqual(self.q.db.execute('SELECT count(*) FROM outbox').fetchone(), (0,))
        self.assertEqual(self.q.prepare().status, 'PREPARED_DURABLE_LOCAL')

    def test_process_death_after_prepare_commit_preserves_nonce(self):
        self.source.write_bytes(self.one_bytes)
        self.crash('prepare', 'after_prepare_commit')
        self.reopen()
        saved = json.loads(self.q.db.execute('SELECT envelope FROM outbox').fetchone()[0])
        self.assertEqual(self.q.prepare().envelope, saved)
        self.assertEqual(self.q.dispatch(self.w.submit).envelope, saved)

    def test_process_death_after_witness_commit_recovers_idempotently(self):
        env = self.first()
        self.crash('dispatch', 'after_witness_ack')
        self.reopen()
        self.assertEqual(self.w.state()['sequence'], 1)
        self.assertEqual(self.q.prepare().envelope, env)
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(self.w.state()['sequence'], 1)

    def test_process_death_after_local_ack_commit_is_already_complete(self):
        self.first()
        self.crash('dispatch', 'after_ack_commit')
        self.reopen()
        self.assertEqual(self.q.dispatch(self.w.submit).status, 'NOTHING_TO_DISPATCH')
        self.assertEqual(self.w.state()['sequence'], 1)

    def crash(self, action, stage):
        proc = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()),
                               '--worker', str(self.root), action, stage],
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 73, proc.stdout + proc.stderr)

    def capacity_state(self, count):
        conn = sqlite3.connect(self.source)
        try:
            state = store._load(conn)
            state['consumed'] = sorted(hashlib.sha256(f'capacity:{i}'.encode()).hexdigest()
                                       for i in range(count))
            state['generation'], state['next_revision'] = count, count + 1
            conn.execute('UPDATE state SET payload=?', (store._encode(state),))
            conn.commit()
            return state
        finally:
            conn.close()

    def test_capacity_4095_to_4096_and_4097_rejected_before_write(self):
        state = self.capacity_state(4095)
        batches, pin = self.capacity_cases[4095]
        result = store.consume_chain(self.source, self.segments, **SCOPE,
                                     expected_state_digest=store._digest(state),
                                     expected_digest=pin, batches=batches)
        self.assertEqual(result.status, 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        conn = sqlite3.connect(self.source)
        try:
            state = store._load(conn)
            self.assertEqual(state['generation'], 4096)
        finally:
            conn.close()
        batches, pin = self.capacity_cases[4096]
        before = self.source.read_bytes()
        result = store.consume_chain(self.source, self.segments, **SCOPE,
                                     expected_state_digest=store._digest(state),
                                     expected_digest=pin, batches=batches)
        self.assertEqual(result.status, 'HISTORY_CAPACITY_EXHAUSTED')
        self.assertEqual(self.source.read_bytes(), before)

    def test_invalid_4097_state_rejected_by_reader_and_queue(self):
        self.capacity_state(4097)
        self.assertEqual(self.q.prepare().status, 'SOURCE_UNAVAILABLE_OR_INVALID')

    def test_all_operational_flags_stay_false(self):
        results = [self.q.prepare(), self.q.dispatch(self.w.submit)]
        self.first()
        results.append(self.q.dispatch(self.w.submit))
        for result in results:
            self.assertFalse(safe_to_promote(result))
            for key, value in asdict(result).items():
                if key not in ('status', 'envelope', 'receipt', 'f3'):
                    self.assertIs(value, False, key)


def load_tests(loader, tests, pattern):
    # Imported A6 harness supplies fixtures, not an extra implicit regression.
    return loader.loadTestsFromTestCase(OutboxTests)


if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker()
    else:
        unittest.main()
