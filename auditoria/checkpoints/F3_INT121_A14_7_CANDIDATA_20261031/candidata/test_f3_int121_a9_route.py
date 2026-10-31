from dataclasses import asdict, replace
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from test_f3_int121_a6_adapter import AdapterTests as FixtureHarness, CLIENT, WITNESS, TRUST, STORE, SCOPE
from f3_int121_a5_sqlite import SQLiteWitness, public_bytes
from f3_int121_a8_atomic_store import AtomicConsumptionStore
from f3_int121_a9_route import RouteConfig, OfflineConsumptionRoute, observe, reconcile, safe_to_promote
from a6_vendor.tools import f3_int109_offline_consumption_store as legacy
from a6_vendor.tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain
from a6_vendor.tools.f3_int106_typed_batch_manifest import TypedBatchEntry


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = FixtureHarness('test_real_project_consumption_matches_a5')
        fixture.setUp()
        try:
            cls.segments = fixture.segments
        finally:
            fixture.doCleanups()
        cls.chains = {}
        for revision in (1, 2):
            batches = (ChainBatch((TypedBatchEntry('audit', f'a9:{revision}'),), revision),)
            result = build_typed_chain(cls.segments, **SCOPE, batches=batches)
            if result.status != 'CHAIN_FIXTURE_UNAUTHENTICATED':
                raise ValueError('Invalid fixture')
            cls.chains[revision] = batches, result.digest
        # Expected after-state pins are computed BEFORE consumption/inquiry.
        state = dict(version=1, generation=0, next_revision=1,
                     scope=list(SCOPE.values()), consumed=[])
        cls.before = legacy._digest(state)
        cls.after = legacy._digest(dict(state, generation=1, next_revision=2,
                                       consumed=[cls.chains[1][1]]))

    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='a9_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'route.sqlite'
        self.config = RouteConfig(STORE, tuple(SCOPE.values()), public_bytes(CLIENT), public_bytes(WITNESS))
        self.route = OfflineConsumptionRoute(self.path, config=self.config, client_private=CLIENT)
        self.assertEqual(self.route.create_new().state_digest, self.before)
        self.w = SQLiteWitness(self.root / 'witness.sqlite', STORE, WITNESS, TRUST, create=True)
        self.addCleanup(self.w.close)

    def consume(self, revision=1, **changes):
        batches, pin = self.chains[revision]
        args = dict(SCOPE, expected_state_digest=self.before if revision == 1 else self.after,
                    expected_digest=pin, batches=batches)
        args.update(changes)
        return self.route.consume_chain(self.segments, **args)

    def inquiry(self, **changes):
        args = dict(config=self.config, before_state_digest=self.before,
                    after_state_digest=self.after, expected_chain_digest=self.chains[1][1])
        args.update(changes)
        return reconcile(self.path, **args)

    def test_complete_route_requires_ack_between_generations(self):
        self.assertEqual(self.consume().status, 'CONSUMED_PENDING_ATTESTATION_LOCAL')
        self.assertEqual(self.consume(2).status, 'ATTESTATION_PENDING')
        self.assertEqual(self.route.dispatch(self.w.submit).status, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(self.consume(2).status, 'CONSUMED_PENDING_ATTESTATION_LOCAL')

    def test_public_key_only_observation_does_not_write(self):
        self.consume()
        before = self.path.read_bytes()
        result = observe(self.path, config=self.config, expected_state_digest=self.after)
        self.assertEqual(result.status, 'PENDING_OBSERVED_LOCAL')
        self.assertEqual(result.snapshot['generation'], 1)
        self.assertEqual(self.path.read_bytes(), before)

    def test_independent_pins_classify_before_pending_and_acknowledged(self):
        self.assertEqual(self.inquiry().status, 'NOT_COMMITTED_OBSERVED_LOCAL')
        self.consume()
        self.assertEqual(self.inquiry().status, 'COMMITTED_PENDING_OBSERVED_LOCAL')
        self.route.dispatch(self.w.submit)
        self.assertEqual(self.inquiry().status, 'COMMITTED_ACKNOWLEDGED_OBSERVED_LOCAL')

    def test_wrong_or_identical_inquiry_pins_never_accept(self):
        self.assertEqual(self.inquiry(after_state_digest=self.before).status, 'INVALID_RECONCILIATION_PIN')
        self.assertEqual(self.inquiry(before_state_digest=None).status, 'INVALID_RECONCILIATION_PIN')
        self.consume()
        self.assertEqual(self.inquiry(after_state_digest='f' * 64).status, 'RECONCILIATION_UNRESOLVED')
        self.assertEqual(self.inquiry(expected_chain_digest='f' * 64).status, 'RECONCILIATION_UNRESOLVED')

    def test_missing_database_has_no_create_or_legacy_fallback(self):
        self.path.rename(self.root / 'preserved.sqlite')
        with patch.object(legacy, 'consume_chain', side_effect=AssertionError('Legacy fallback forbidden')):
            result = self.consume()
        self.assertEqual(result.status, 'DATABASE_UNAVAILABLE_OR_INVALID')
        self.assertFalse(self.path.exists())

    def test_corrupt_database_is_preserved_without_fallback(self):
        self.path.write_bytes(b'not a SQLite database')
        with patch.object(legacy, 'consume_chain', side_effect=AssertionError('Legacy fallback forbidden')):
            self.assertEqual(self.consume().status, 'DATABASE_UNAVAILABLE_OR_INVALID')
        self.assertEqual(self.path.read_bytes(), b'not a SQLite database')

    def test_existing_legacy_database_is_not_silently_upgraded(self):
        old = self.root / 'old.sqlite'
        legacy.create_store(old, **SCOPE, minimum_revision=1)
        route = OfflineConsumptionRoute(old, config=self.config, client_private=CLIENT)
        before = old.read_bytes()
        batches, pin = self.chains[1]
        with patch.object(legacy, 'consume_chain', side_effect=AssertionError('Fallback forbidden')):
            result = route.consume_chain(self.segments, **SCOPE, batches=batches,
                                         expected_digest=pin, expected_state_digest=self.before)
        self.assertEqual(result.status, 'DATABASE_UNAVAILABLE_OR_INVALID')
        self.assertEqual(old.read_bytes(), before)

    def test_create_existing_never_overwrites(self):
        before = self.path.read_bytes()
        self.assertEqual(self.route.create_new().status, 'DATABASE_EXISTS')
        self.assertEqual(self.path.read_bytes(), before)

    def test_wrong_signing_key_is_rejected_before_open(self):
        with self.assertRaises(ValueError):
            OfflineConsumptionRoute(self.path, config=self.config, client_private=WITNESS)

    def test_wrong_pinned_witness_or_store_rejects_existing_database(self):
        for config in (replace(self.config, store_id='OTHER'),
                       replace(self.config, witness_public=public_bytes(CLIENT))):
            route = OfflineConsumptionRoute(self.path, config=config, client_private=CLIENT)
            self.assertEqual(route.dispatch(self.w.submit).status, 'DATABASE_FORMAT_OR_IDENTITY_REJECTED')

    def test_copy_empty_legacy_preserves_source_and_revision(self):
        source = self.root / 'legacy.sqlite'
        initial = legacy.create_store(source, **SCOPE, minimum_revision=7)
        target = self.root / 'copied.sqlite'
        route = OfflineConsumptionRoute(target, config=self.config, client_private=CLIENT)
        before = source.read_bytes()
        result = route.copy_empty_legacy(source, expected_state_digest=initial.state_digest)
        self.assertEqual(result.status, 'EMPTY_LEGACY_COPIED_LOCAL')
        self.assertEqual(source.read_bytes(), before)
        result = observe(target, config=self.config, expected_state_digest=initial.state_digest)
        self.assertEqual(result.status, 'ACKNOWLEDGED_OR_INITIAL_LOCAL')

    def test_copy_advanced_legacy_is_explicitly_rejected(self):
        source = self.root / 'advanced.sqlite'
        legacy.create_store(source, **SCOPE, minimum_revision=1)
        batches, pin = self.chains[1]
        result = legacy.consume_chain(source, self.segments, **SCOPE, batches=batches,
                                      expected_digest=pin, expected_state_digest=self.before)
        target = self.root / 'unsupported.sqlite'
        route = OfflineConsumptionRoute(target, config=self.config, client_private=CLIENT)
        before = source.read_bytes()
        self.assertEqual(route.copy_empty_legacy(source, expected_state_digest=result.state_digest).status,
                         'MIGRATION_HISTORY_REQUIRES_SEPARATE_PROCEDURE')
        self.assertFalse(target.exists())
        self.assertEqual(source.read_bytes(), before)

    def test_copy_wrong_pin_and_scope_do_not_create_destination(self):
        source = self.root / 'legacy.sqlite'
        legacy.create_store(source, **SCOPE, minimum_revision=1)
        target = self.root / 'new.sqlite'
        route = OfflineConsumptionRoute(target, config=self.config, client_private=CLIENT)
        self.assertEqual(route.copy_empty_legacy(source, expected_state_digest='f' * 64).status, 'STATE_ANCHOR_MISMATCH')
        wrong = replace(self.config, scope=('audit:B', 'review', 'run:1'))
        route = OfflineConsumptionRoute(target, config=wrong, client_private=CLIENT)
        self.assertEqual(route.copy_empty_legacy(source, expected_state_digest=self.before).status, 'STORE_SCOPE_MISMATCH')
        self.assertFalse(target.exists())

    def test_copy_same_path_existing_target_and_extra_schema_rejected(self):
        source = self.root / 'legacy.sqlite'
        legacy.create_store(source, **SCOPE, minimum_revision=1)
        same = OfflineConsumptionRoute(source, config=self.config, client_private=CLIENT)
        self.assertEqual(same.copy_empty_legacy(source, expected_state_digest=self.before).status,
                         'MIGRATION_REQUIRES_NEW_DESTINATION')
        self.assertEqual(self.route.copy_empty_legacy(source, expected_state_digest=self.before).status, 'DATABASE_EXISTS')
        conn = sqlite3.connect(source)
        try:
            conn.execute('CREATE TABLE unexpected (x INTEGER)')
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self.route.copy_empty_legacy(source, expected_state_digest=self.before).status,
                         'MIGRATION_SOURCE_NOT_LEGACY_STATE_ONLY')

    def test_lost_witness_response_recovers_without_new_consumption(self):
        env = self.consume().envelope
        def lost(envelope):
            self.w.submit(envelope)
            raise TimeoutError('Lost ACK after witness commit')
        self.assertEqual(self.route.dispatch(lost).status, 'WITNESS_UNAVAILABLE_OR_UNCERTAIN')
        self.assertEqual(self.consume(2).status, 'ATTESTATION_PENDING')
        self.assertEqual(self.inquiry().status, 'COMMITTED_PENDING_OBSERVED_LOCAL')
        self.assertEqual(self.route.dispatch(self.w.submit).envelope, env)
        self.assertEqual(self.w.state()['sequence'], 1)

    def test_copy_sqlite_like_user_table_is_not_ignored(self):
        source = self.root / 'legacy.sqlite'
        legacy.create_store(source, **SCOPE, minimum_revision=1)
        conn = sqlite3.connect(source)
        try:
            conn.execute('CREATE TABLE sqlitex_extra (x INTEGER)')
            conn.commit()
        finally:
            conn.close()
        target = self.root / 'new.sqlite'
        route = OfflineConsumptionRoute(target, config=self.config, client_private=CLIENT)
        self.assertEqual(route.copy_empty_legacy(source, expected_state_digest=self.before).status,
                         'MIGRATION_SOURCE_NOT_LEGACY_STATE_ONLY')
        self.assertFalse(target.exists())

    def test_audit_ignored_source_update_cannot_report_consumed(self):
        self.sql("CREATE TRIGGER ignore_write BEFORE UPDATE ON state BEGIN SELECT RAISE(IGNORE); END")
        self.assertEqual(self.consume().status, 'ATTESTATION_STATE_MISMATCH')
        self.assertEqual(self.inquiry().status, 'NOT_COMMITTED_OBSERVED_LOCAL')

    def test_audit_ignored_outbox_insert_rolls_back_source(self):
        self.sql("CREATE TRIGGER ignore_write BEFORE INSERT ON outbox BEGIN SELECT RAISE(IGNORE); END")
        self.assertEqual(self.consume().status, 'ATTESTATION_STATE_MISMATCH')
        self.assertEqual(self.inquiry().status, 'NOT_COMMITTED_OBSERVED_LOCAL')

    def test_audit_ignored_ack_does_not_release_next_generation(self):
        self.consume()
        self.sql("CREATE TRIGGER ignore_ack BEFORE UPDATE ON outbox BEGIN SELECT RAISE(IGNORE); END")
        self.assertEqual(self.route.dispatch(self.w.submit).status, 'ATTESTATION_STATE_MISMATCH')
        self.assertEqual(self.consume(2).status, 'ATTESTATION_PENDING')
        self.assertEqual(self.inquiry().status, 'COMMITTED_PENDING_OBSERVED_LOCAL')

    def test_audit_unknown_outcome_after_commit_is_observable(self):
        def fault(stage):
            if stage == 'after_consumption_commit':
                raise legacy.SimulatedInterruption()
        store = AtomicConsumptionStore(self.path, store_id=STORE, scope=self.config.scope,
                                       client_private=CLIENT, witness_public=self.config.witness_public,
                                       _fault=fault)
        try:
            batches, pin = self.chains[1]
            result = store.consume(self.segments, **SCOPE, batches=batches,
                                   expected_digest=pin, expected_state_digest=self.before)
            self.assertEqual(result.status, 'COMMIT_OUTCOME_UNKNOWN')
        finally:
            store.close()
        self.assertEqual(self.inquiry().status, 'COMMITTED_PENDING_OBSERVED_LOCAL')

    def test_invalid_config_and_pins_fail_before_reading(self):
        self.assertEqual(observe(self.path, config=None, expected_state_digest=self.before).status,
                         'INVALID_ROUTE_CONFIG')
        self.assertEqual(observe(self.path, config=self.config, expected_state_digest=None).status,
                         'INVALID_STATE_ANCHOR')
        self.assertEqual(self.inquiry(config=None).status, 'INVALID_ROUTE_CONFIG')

    def test_wrong_observation_anchor_is_not_replaced(self):
        self.consume()
        self.assertEqual(observe(self.path, config=self.config, expected_state_digest=self.before).status,
                         'STATE_ANCHOR_MISMATCH')

    def test_all_operational_locks_remain_false(self):
        results = [observe(self.path, config=self.config, expected_state_digest=self.before), self.inquiry(),
                   self.consume(), self.route.dispatch(self.w.submit)]
        for result in results:
            self.assertFalse(safe_to_promote(result))
            for field in ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
                          'native_prototype_authorized', 'strict_deadline_guaranteed', 'authenticated_witness_verified'):
                self.assertIs(asdict(result)[field], False)

    def sql(self, statement):
        conn = sqlite3.connect(self.path)
        try:
            conn.execute(statement)
            conn.commit()
        finally:
            conn.close()


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(RouteTests)


if __name__ == '__main__':
    unittest.main()
