"""A6: fresh signed local witness query + read-only project SQLite adapter.

Not a network service or proof of independent custody. A positive result is a
point-in-time local comparison. Joint rollback of both stores is still possible.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from f3_int121_a5_sqlite import canonical, digest, valid_hex, ZERO, MAX_INTEGER
from a6_vendor.tools.f3_int109_offline_consumption_store import _load, _digest


@dataclass(frozen=True)
class AdapterResult:
    status: str
    f3: str = 'OPEN'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


class WitnessUnavailable(Exception):
    pass


class LocalChallengeResponder:
    """Local service boundary for tests; uses A5's pinned signing identity.

    Reads the head and receipt in the same SQLite snapshot. No network, public
    listener, new credentials or custody configuration are created here.
    """
    def __init__(self, witness):
        self.witness = witness

    def answer(self, challenge):
        if not valid_hex(challenge, 64):
            raise ValueError('Invalid challenge')
        w = self.witness
        if not w.available:
            raise WitnessUnavailable('Witness unavailable')
        w.db.execute('BEGIN')
        try:
            sequence, head, _ = w._read_chain()
            row = w.db.execute('SELECT receipt FROM receipts WHERE sequence=?',
                               (sequence,)).fetchone()
            record = dict(schema='F3-INT-121-A6-QUERY', store_id=w.store_id,
                          challenge=challenge, sequence=sequence, generation=sequence,
                          head=head, receipt=json.loads(row[0]) if row else None,
                          key_id=hashlib.sha256(w.public).hexdigest())
            response = dict(record=record, signature=w.private.sign(canonical(record)).hex())
            return response
        finally:
            w.db.rollback()


class FreshQuery:
    """One outstanding challenge per instance; every check consumes it.

    Timeout uses the local monotonic clock. Restart discards outstanding
    challenges; the caller must issue a new one. This is not a persisted anchor.
    """
    def __init__(self, *, expected_store_id, witness_public, expected_scope,
                 ttl_seconds=5.0, _clock=time.monotonic):
        if type(expected_store_id) is not str or not 0 < len(expected_store_id) <= 128:
            raise ValueError('Invalid store identity')
        if type(witness_public) is not bytes or len(witness_public) != 32:
            raise ValueError('Invalid pinned witness key')
        if (type(expected_scope) is not tuple or len(expected_scope) != 3
                or any(type(x) is not str or not x for x in expected_scope)):
            raise ValueError('Invalid expected scope')
        if type(ttl_seconds) not in (int, float) or not 0 < ttl_seconds <= 60:
            raise ValueError('Invalid timeout')
        self.store_id = expected_store_id
        self.public = witness_public
        self.scope = expected_scope
        self.ttl = ttl_seconds
        self.clock = _clock
        self.pending = None

    def issue(self):
        challenge = secrets.token_hex(32)
        self.pending = (challenge, self.clock())
        return challenge

    def check(self, database_path, response):
        pending, self.pending = self.pending, None
        if pending is None:
            return AdapterResult('NO_PENDING_CHALLENGE')
        challenge, started = pending
        elapsed = self.clock() - started
        if not 0 <= elapsed < self.ttl:
            return AdapterResult('CHALLENGE_EXPIRED')
        try:
            response = json.loads(canonical(response))
            if type(response) is not dict or set(response) != {'record', 'signature'}:
                return AdapterResult('INVALID_RESPONSE')
            record = response['record']
            fields = {'schema', 'store_id', 'challenge', 'sequence', 'generation',
                      'head', 'receipt', 'key_id'}
            if type(record) is not dict or set(record) != fields:
                return AdapterResult('INVALID_RESPONSE')
            if (record['schema'] != 'F3-INT-121-A6-QUERY'
                    or record['store_id'] != self.store_id
                    or record['key_id'] != hashlib.sha256(self.public).hexdigest()):
                return AdapterResult('WITNESS_CONTEXT_MISMATCH')
            if record['challenge'] != challenge:
                return AdapterResult('CHALLENGE_MISMATCH')
            if (type(record['sequence']) is not int
                    or not 0 <= record['sequence'] <= MAX_INTEGER
                    or type(record['generation']) is not int
                    or record['generation'] != record['sequence']
                    or not valid_hex(record['head'], 64)
                    or not valid_hex(response['signature'], 128)):
                return AdapterResult('INVALID_RESPONSE')
            public = Ed25519PublicKey.from_public_bytes(self.public)
            public.verify(bytes.fromhex(response['signature']), canonical(record))
            receipt = record['receipt']
            if record['sequence'] == 0:
                if receipt is not None or record['head'] != ZERO:
                    return AdapterResult('INVALID_RECEIPT')
                return AdapterResult('UNWITNESSED_STATE')
            if type(receipt) is not dict or set(receipt) != {'record', 'signature'}:
                return AdapterResult('INVALID_RECEIPT')
            r = receipt['record']
            receipt_fields = {'schema', 'store_id', 'sequence', 'generation', 'state_digest',
                              'nonce', 'previous_receipt_digest', 'request_digest'}
            if (type(r) is not dict or set(r) != receipt_fields
                    or r['schema'] != 'F3-INT-121-A4-RECEIPT'
                    or r['store_id'] != self.store_id
                    or type(r['sequence']) is not int or r['sequence'] != record['sequence']
                    or type(r['generation']) is not int or r['generation'] != record['generation']
                    or any(not valid_hex(r[k], 64) for k in
                           ('state_digest', 'nonce', 'previous_receipt_digest', 'request_digest'))
                    or not valid_hex(receipt['signature'], 128)
                    or digest(receipt) != record['head']):
                return AdapterResult('INVALID_RECEIPT')
            public.verify(bytes.fromhex(receipt['signature']), canonical(r))
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, InvalidSignature):
            return AdapterResult('INVALID_RESPONSE_OR_SIGNATURE')
        result = self._compare_database(database_path, r)
        if not 0 <= self.clock() - started < self.ttl:
            return AdapterResult('CHALLENGE_EXPIRED')
        return result

    def _compare_database(self, path, receipt_record):
        connection = None
        try:
            path = Path(path).resolve(strict=True)
            if not path.is_file():
                return AdapterResult('INVALID_DATABASE_PATH')
            connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True,
                                          timeout=0, isolation_level=None)
            connection.execute('PRAGMA trusted_schema=OFF')
            connection.execute('PRAGMA query_only=ON')
            connection.execute('BEGIN')
            if connection.execute('PRAGMA journal_mode').fetchone() != ('delete',):
                return AdapterResult('UNSUPPORTED_JOURNAL_MODE')
            state = _load(connection)
            if state['scope'] != list(self.scope):
                return AdapterResult('SQLITE_SCOPE_MISMATCH')
            if state['generation'] != receipt_record['generation']:
                return AdapterResult('SQLITE_GENERATION_MISMATCH')
            if _digest(state) != receipt_record['state_digest']:
                return AdapterResult('SQLITE_DIGEST_MISMATCH')
            return AdapterResult('SQLITE_WITNESS_FRESH_LOCAL_MATCH')
        except FileNotFoundError:
            return AdapterResult('DATABASE_NOT_FOUND')
        except sqlite3.DatabaseError:
            return AdapterResult('SQLITE_READ_ERROR')
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            return AdapterResult('INVALID_DATABASE_OR_STATE')
        finally:
            if connection is not None:
                connection.close()


def safe_to_promote(_result):
    return False
