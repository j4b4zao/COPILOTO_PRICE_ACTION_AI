import base64
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from f3_int121_a5_sqlite import SQLiteWitness, canonical, digest, public_bytes, ZERO
from f3_int121_a6_adapter import FreshQuery, LocalChallengeResponder, WitnessUnavailable, safe_to_promote
from a6_vendor.tools import f3_int109_offline_consumption_store as store
from a6_vendor.tools.f3_int98_policy_bundle_registry import (
    PolicyBundleRecord, PolicyEvidenceRegistry, PolicyEvidenceReceipt,
)
from a6_vendor.tools.f3_int101_cross_batch_audit import AuditSegment
from a6_vendor.tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain
from a6_vendor.tools.f3_int106_typed_batch_manifest import TypedBatchEntry

# Public deterministic seeds solely for synthetic tests.
CLIENT = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
WITNESS = Ed25519PrivateKey.from_private_bytes(bytes(range(32, 64)))
KEY_ID = hashlib.sha256(public_bytes(CLIENT)).hexdigest()
TRUST = {KEY_ID: public_bytes(CLIENT)}
STORE = 'COPILOTO_LOCAL_TEST'
SCOPE = dict(context='audit:A', purpose='review', run_id='run:1')


class AdapterTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='a6_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'project.sqlite'
        self.wpath = self.root / 'witness.sqlite'
        self.w = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST, create=True)
        self.addCleanup(self.w.close)
        self.responder = LocalChallengeResponder(self.w)
        self.now = 10.0
        self.q = self.query()
        f = json.loads(Path(__file__).with_name('A6_TEST_FIXTURE.json').read_text())
        self.segments = (AuditSegment(
            (PolicyBundleRecord(base64.b64decode(f['blob']), f['sha']),),
            tuple(PolicyEvidenceReceipt(*r) for r in f['receipts']),
            PolicyEvidenceRegistry(tuple(f['references']), f['namespace']), f['tip']),)
        initial = store.create_store(self.db, **SCOPE, minimum_revision=1)
        self.assertEqual(initial.status, 'STORE_FIXTURE_UNAUTHENTICATED')
        self.anchor = initial.state_digest

    def query(self, **changes):
        args = dict(expected_store_id=STORE, witness_public=public_bytes(WITNESS),
                    expected_scope=tuple(SCOPE.values()), _clock=lambda: self.now)
        args.update(changes)
        return FreshQuery(**args)

    def consume(self, revision):
        batches = (ChainBatch((TypedBatchEntry('audit', f'x{revision}'),), revision),)
        chain = build_typed_chain(self.segments, **SCOPE, batches=batches)
        self.assertEqual(chain.status, 'CHAIN_FIXTURE_UNAUTHENTICATED')
        result = store.consume_chain(self.db, self.segments, **SCOPE,
                                     expected_state_digest=self.anchor,
                                     expected_digest=chain.digest, batches=batches)
        self.assertEqual(result.status, 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.anchor = result.state_digest

    def attest(self, generation):
        state = self.w.state()
        req = dict(schema='F3-INT-121-A4-LOCAL', store_id=STORE,
                   sequence=generation, generation=generation,
                   state_digest=self.anchor, previous_receipt_digest=state['head'],
                   nonce=secrets.token_hex(32))
        env = dict(request=req, key_id=KEY_ID, signature=CLIENT.sign(canonical(req)).hex())
        result = self.w.submit(env)
        self.assertEqual(result[0], 'CONFIRMED')
        return env

    def check(self, response=None):
        if response is None:
            response = self.responder.answer(self.q.issue())
        return self.q.check(self.db, response)

    def bootstrap(self):
        self.consume(1)
        self.attest(1)

    def resign(self, response):
        response['signature'] = WITNESS.sign(canonical(response['record'])).hex()
        return response

    def test_real_project_consumption_matches_a5(self):
        self.bootstrap()
        before = self.db.read_bytes()
        result = self.check()
        self.assertEqual(result.status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')
        self.assertEqual(self.db.read_bytes(), before)

    def test_two_generations_and_reopen(self):
        self.bootstrap()
        self.consume(2)
        self.attest(2)
        self.w.close()
        self.w = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST)
        self.addCleanup(self.w.close)
        self.responder = LocalChallengeResponder(self.w)
        self.assertEqual(self.check().status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')

    def test_empty_witness_fails_closed(self):
        self.assertEqual(self.check().status, 'UNWITNESSED_STATE')

    def test_unattested_project_commit_rejected(self):
        self.bootstrap()
        self.consume(2)
        self.assertEqual(self.check().status, 'SQLITE_GENERATION_MISMATCH')
        # Reconciliation requires the exact observed next state, then requery.
        self.attest(2)
        self.assertEqual(self.check().status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')

    def test_source_only_rollback_rejected(self):
        self.bootstrap()
        snapshot = self.db.read_bytes()
        self.consume(2)
        self.attest(2)
        self.db.write_bytes(snapshot)
        self.assertEqual(self.check().status, 'SQLITE_GENERATION_MISMATCH')

    def test_witness_only_rollback_rejected(self):
        self.bootstrap()
        snapshot = self.wpath.read_bytes()
        self.consume(2)
        self.attest(2)
        self.w.close()
        self.wpath.write_bytes(snapshot)
        self.w = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST)
        self.addCleanup(self.w.close)
        self.responder = LocalChallengeResponder(self.w)
        self.assertEqual(self.check().status, 'SQLITE_GENERATION_MISMATCH')

    def test_joint_valid_rollback_remains_explicit_limitation(self):
        self.bootstrap()
        db_snapshot, w_snapshot = self.db.read_bytes(), self.wpath.read_bytes()
        self.consume(2)
        self.attest(2)
        self.w.close()
        self.db.write_bytes(db_snapshot)
        self.wpath.write_bytes(w_snapshot)
        self.w = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST)
        self.addCleanup(self.w.close)
        self.responder = LocalChallengeResponder(self.w)
        # A fresh signature from a rolled-back LOCAL witness is still valid.
        self.assertEqual(self.check().status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')

    def test_reused_response_rejected(self):
        self.bootstrap()
        response = self.responder.answer(self.q.issue())
        self.assertEqual(self.check(response).status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')
        self.assertEqual(self.check(response).status, 'NO_PENDING_CHALLENGE')

    def test_old_response_cannot_satisfy_new_query(self):
        self.bootstrap()
        old = self.responder.answer(self.q.issue())
        self.q.issue()
        self.assertEqual(self.check(old).status, 'CHALLENGE_MISMATCH')

    def test_restart_drops_pending_query(self):
        self.bootstrap()
        response = self.responder.answer(self.q.issue())
        self.q = self.query()
        self.assertEqual(self.check(response).status, 'NO_PENDING_CHALLENGE')

    def test_expired_and_reversed_clock_rejected(self):
        self.bootstrap()
        for elapsed in (5.0, 6.0, -1.0):
            response = self.responder.answer(self.q.issue())
            self.now += elapsed
            self.assertEqual(self.check(response).status, 'CHALLENGE_EXPIRED')

    def test_tampering_and_unknown_signer_rejected(self):
        self.bootstrap()
        response = self.responder.answer(self.q.issue())
        response['record']['head'] = 'f' * 64
        self.assertEqual(self.check(response).status, 'INVALID_RESPONSE_OR_SIGNATURE')
        response = self.responder.answer(self.q.issue())
        response['signature'] = CLIENT.sign(canonical(response['record'])).hex()
        self.assertEqual(self.check(response).status, 'INVALID_RESPONSE_OR_SIGNATURE')

    def test_wrong_pinned_key_and_store_rejected(self):
        self.bootstrap()
        for changes in (dict(witness_public=public_bytes(CLIENT)), dict(expected_store_id='OTHER')):
            self.q = self.query(**changes)
            self.assertEqual(self.check().status, 'WITNESS_CONTEXT_MISMATCH')

    def test_bad_signed_receipt_binding_rejected(self):
        self.bootstrap()
        response = self.responder.answer(self.q.issue())
        response['record']['receipt']['record']['sequence'] = True
        response['record']['head'] = digest(response['record']['receipt'])
        self.assertEqual(self.check(self.resign(response)).status, 'INVALID_RECEIPT')

    def test_corrupt_inner_receipt_signature_rejected(self):
        self.bootstrap()
        response = self.responder.answer(self.q.issue())
        response['record']['receipt']['signature'] = '0' * 128
        response['record']['head'] = digest(response['record']['receipt'])
        self.assertEqual(self.check(self.resign(response)).status, 'INVALID_RESPONSE_OR_SIGNATURE')

    def test_unavailable_witness_no_fallback(self):
        self.bootstrap()
        challenge = self.q.issue()
        self.w.available = False
        with self.assertRaises(WitnessUnavailable):
            self.responder.answer(challenge)
        self.assertEqual(self.q.check(self.db, None).status,
                         'INVALID_RESPONSE')

    def test_same_generation_digest_change_rejected(self):
        self.bootstrap()
        conn = sqlite3.connect(self.db)
        try:
            state = store._load(conn)
            state['next_revision'] += 1
            conn.execute('UPDATE state SET payload=?', (store._encode(state),))
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self.check().status, 'SQLITE_DIGEST_MISMATCH')

    def test_scope_is_pinned_separately(self):
        self.bootstrap()
        self.q = self.query(expected_scope=('audit:A', 'review', 'run:OTHER'))
        self.assertEqual(self.check().status, 'SQLITE_SCOPE_MISMATCH')

    def test_missing_source_never_created(self):
        self.bootstrap()
        missing = self.root / 'missing.sqlite'
        response = self.responder.answer(self.q.issue())
        self.assertEqual(self.q.check(missing, response).status, 'DATABASE_NOT_FOUND')
        self.assertFalse(missing.exists())

    def test_busy_source_fails_closed(self):
        self.bootstrap()
        conn = sqlite3.connect(self.db, isolation_level=None)
        try:
            conn.execute('BEGIN EXCLUSIVE')
            self.assertEqual(self.check().status, 'SQLITE_READ_ERROR')
        finally:
            conn.close()

    def test_invalid_source_schema_rejected(self):
        self.bootstrap()
        conn = sqlite3.connect(self.db)
        try:
            conn.execute('UPDATE state SET payload=?', (b'{}',))
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self.check().status, 'INVALID_DATABASE_OR_STATE')

    def test_wal_mode_rejected(self):
        self.bootstrap()
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(conn.execute('PRAGMA journal_mode=WAL').fetchone(), ('wal',))
            self.assertEqual(self.check().status, 'UNSUPPORTED_JOURNAL_MODE')
        finally:
            conn.close()

    def test_unknown_fields_and_malformed_response_rejected(self):
        self.bootstrap()
        for malformed in (None, [], {'record': {}}, {'record': {}, 'signature': '0' * 128}):
            self.q.issue()
            self.assertNotEqual(self.q.check(self.db, malformed).status, 'SQLITE_WITNESS_FRESH_LOCAL_MATCH')
        response = self.responder.answer(self.q.issue())
        response['record']['extra'] = 1
        self.assertEqual(self.check(self.resign(response)).status, 'INVALID_RESPONSE')

    def test_every_operational_lock_remains_false(self):
        self.bootstrap()
        good = self.check()
        bad = self.q.check(self.db, None)
        for result in (good, bad):
            self.assertFalse(safe_to_promote(result))
            for key, value in asdict(result).items():
                if key not in ('status', 'f3'):
                    self.assertIs(value, False, key)


if __name__ == '__main__':
    unittest.main()
