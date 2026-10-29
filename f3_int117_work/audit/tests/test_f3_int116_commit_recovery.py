"""Controlled commit errors, real SQLite locking and retained offline anchors."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from dataclasses import asdict
import test_f3_int109_offline_consumption_store as prior
from tools import f3_int109_offline_consumption_store as store
from tools.f3_int115_multiprocess_recovery import observe_recovery
from tools.f3_int114_custody_recovery import LOCKS
from tools.f3_int116_commit_recovery import commit_probe, safe_to_promote


class CommitRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ConsumptionStoreTests.setUpClass()
        cls.source = prior.ConsumptionStoreTests

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'ledger.sqlite'
        self.initial = store.create_store(self.path, **self.source.scope, minimum_revision=1)
        self.assertEqual(self.initial.status, 'STORE_FIXTURE_UNAUTHENTICATED')
        self.before = dict(version=1, generation=0, next_revision=1,
                           scope=list(self.source.scope.values()), consumed=[])
        self.after = dict(self.before, generation=1, next_revision=2, consumed=[self.source.pin])
        self.pins = dict(before_state_digest=self.initial.state_digest,
                         after_state_digest=store._digest(self.after),
                         expected_chain_digest=self.source.pin, **self.source.scope)
        self.reference = Path(self.temp.name) / 'retained.json'
        self.retained = json.dumps(self.pins, sort_keys=True).encode('ascii')
        self.reference.write_bytes(self.retained)
        self.addCleanup(lambda: self.assertEqual(self.reference.read_bytes(), self.retained))

    def consume(self, anchor=None):
        result = store.consume_chain(self.path, self.source.segments,
            expected_state_digest=anchor or self.initial.state_digest,
            expected_digest=self.source.pin, batches=self.source.batches, **self.source.scope)
        self.safety(result)
        return result

    def safety(self, result):
        values = asdict(result)
        self.assertEqual(values['f3'], 'OPEN')
        for flag in LOCKS:
            self.assertIs(values[flag], False)

    def reopen(self, committed):
        connection = sqlite3.connect(self.path)
        try:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual(connection.execute('SELECT count(*) FROM state').fetchone(), (1,))
            state = store._load(connection)
        finally:
            connection.close()
        self.assertEqual(state, self.after if committed else self.before)
        pins = json.loads(self.reference.read_bytes())
        result = observe_recovery(self.path, ack_state='UNKNOWN', **pins)
        self.safety(result)
        self.assertFalse(result.retry_allowed)
        self.assertEqual(result.ack_state, 'UNKNOWN')
        self.assertEqual(result.status, ('COMMITTED' if committed else 'NOT_COMMITTED') + '_OBSERVED_UNAUTHENTICATED')
        print(json.dumps(dict(test=self.id(), reconciliation=asdict(result))), flush=True)

    def experiment(self, mode):
        with commit_probe(mode) as probes:
            result = self.consume()
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].events[-1], 'connection_closed')
        print(json.dumps(dict(test=self.id(), mode=mode, events=probes[0].events,
                              result=asdict(result))), flush=True)
        return result, probes[0].events

    def test_normal_commit_control(self):
        result, events = self.experiment('normal')
        self.assertEqual(result.status, 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertIn('sqlite_commit_returned', events)
        self.reopen(True)

    def test_error_before_commit_rolls_back_on_close(self):
        result, events = self.experiment('before_error')
        self.assertEqual(result.status, 'STORE_ERROR')
        self.assertIn('injected_before_sqlite_commit', events)
        self.assertNotIn('sqlite_commit_returned', events)
        self.reopen(False)

    def test_sqlite_authorizer_denies_commit(self):
        result, events = self.experiment('deny_commit')
        self.assertEqual(result.status, 'STORE_ERROR')
        self.assertIn('sqlite_authorizer_denied_commit', events)
        self.assertIn('sqlite_commit_raised', events)
        self.reopen(False)

    def test_real_reader_blocks_commit_without_partial_state(self):
        reader = sqlite3.connect(self.path, timeout=0, isolation_level=None)
        try:
            reader.execute('BEGIN')
            reader.execute('SELECT payload FROM state').fetchall()
            result, events = self.experiment('normal')
            self.assertEqual(result.status, 'STORE_BUSY')
            self.assertIn('sqlite_commit_raised', events)
            self.assertNotIn('sqlite_commit_returned', events)
        finally:
            reader.close()
        self.reopen(False)

    def test_post_commit_error_reconciles_and_rejects_both_replays(self):
        result, events = self.experiment('after_error')
        self.assertEqual(result.status, 'STORE_ERROR')
        self.assertIn('sqlite_commit_returned', events)
        self.assertIn('injected_after_sqlite_commit', events)
        self.reopen(True)
        self.assertEqual(self.consume().status, 'STATE_ANCHOR_MISMATCH')
        # Current anchor must not turn the already consumed chain into new work.
        self.assertEqual(self.consume(self.pins['after_state_digest']).status,
                         'STALE_CHAIN_REVISION')
        self.reopen(True)

    def test_wrong_retained_after_anchor_fails_unresolved(self):
        self.experiment('after_error')
        pins = dict(self.pins, after_state_digest='0' * 64)
        result = observe_recovery(self.path, ack_state='LOST', **pins)
        self.assertEqual(result.status, 'RECONCILIATION_UNRESOLVED')
        self.assertFalse(result.retry_allowed)
        self.safety(result)
        self.reopen(True)

    def test_missing_store_is_not_recreated(self):
        missing = self.path.with_name('missing.sqlite')
        result = observe_recovery(missing, **self.pins)
        self.assertEqual(result.status, 'STORE_ERROR')
        self.assertFalse(missing.exists())
        self.assertFalse(result.retry_allowed)
        self.safety(result)

    def test_invalid_mode_and_promotion_remain_closed(self):
        with self.assertRaises(ValueError):
            with commit_probe('unsupported'):
                self.fail('Invalid mode entered')
        self.assertFalse(safe_to_promote())


if __name__ == '__main__':
    unittest.main()
