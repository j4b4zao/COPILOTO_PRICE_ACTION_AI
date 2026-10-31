"""A7: durable local post-commit attestation queue, not a live trading path.

Source commit and queue preparation are separate transactions. A generation gap
is rejected, never fabricated/backfilled. Caller must serialize source commits
and drain this queue before advancing. Independent custody is still required.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from f3_int121_a5_sqlite import (
    IntegrityError, ZERO, canonical, digest, public_bytes, valid_hex, verify,
)
from a6_vendor.tools.f3_int109_offline_consumption_store import _load, _digest


@dataclass(frozen=True)
class OutboxResult:
    status: str
    envelope: dict | None = None
    receipt: dict | None = None
    f3: str = 'OPEN'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


class SourceError(Exception):
    pass


class AttestationOutbox:
    def __init__(self, path, source_path, *, store_id, scope, client_private,
                 witness_public, create=False, timeout=1.0, _fault=None):
        if type(store_id) is not str or not 0 < len(store_id) <= 128:
            raise ValueError('Invalid store identity')
        if type(scope) is not tuple or len(scope) != 3 or any(type(x) is not str or not x for x in scope):
            raise ValueError('Invalid scope')
        if type(witness_public) is not bytes or len(witness_public) != 32:
            raise ValueError('Invalid witness public key')
        self.path, self.source = Path(path).resolve(), Path(source_path).resolve()
        if self.path == self.source:
            raise ValueError('Queue and source must be separate files')
        self.scope, self.store_id = scope, store_id
        self.private, self.public = client_private, public_bytes(client_private)
        self.client_id = hashlib.sha256(self.public).hexdigest()
        self.witness_public = witness_public
        self.config = dict(version=1, store_id=store_id, scope=list(scope),
                           client_public=self.public.hex(), witness_public=witness_public.hex())
        self._fault = _fault or (lambda stage: None)
        self.db = None
        try:
            initial_digest = None
            if create:
                source, state = self._source_snapshot()
                try:
                    if state['generation'] != 0:
                        raise SourceError('BOOTSTRAP_REQUIRES_GENERATION_ZERO')
                    initial_digest = _digest(state)
                finally:
                    source.close()
                with self.path.open('xb'):
                    pass
            self.db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True,
                                      isolation_level=None, timeout=timeout)
            self.db.execute('PRAGMA trusted_schema=OFF')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.execute('PRAGMA journal_mode=DELETE')
            if create:
                self.db.execute('BEGIN IMMEDIATE')
                self.db.execute('CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), config TEXT NOT NULL, initial_digest TEXT NOT NULL)')
                self.db.execute('CREATE TABLE outbox (sequence INTEGER PRIMARY KEY, envelope TEXT NOT NULL, receipt TEXT)')
                self.db.execute('INSERT INTO metadata VALUES (1, ?, ?)',
                                (canonical(self.config).decode(), initial_digest))
                self.db.commit()
            self.db.execute('BEGIN')
            self._ledger()
            self.db.rollback()
        except BaseException:
            if self.db is not None:
                self.db.close()
            raise

    def _source_snapshot(self):
        conn = None
        try:
            path = self.source.resolve(strict=True)
            conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True,
                                   isolation_level=None, timeout=0)
            conn.execute('PRAGMA trusted_schema=OFF')
            conn.execute('PRAGMA query_only=ON')
            conn.execute('BEGIN')
            if conn.execute('PRAGMA journal_mode').fetchone() != ('delete',):
                raise SourceError('Unsupported journal mode')
            state = _load(conn)
            if state['scope'] != list(self.scope):
                raise SourceError('Scope mismatch')
            return conn, state
        except (OSError, sqlite3.Error, ValueError, TypeError, UnicodeError, RecursionError, SourceError) as exc:
            if conn is not None:
                conn.close()
            raise SourceError('Invalid or unavailable source') from exc

    def _valid_receipt(self, receipt, envelope):
        try:
            expected = dict(envelope['request'], schema='F3-INT-121-A4-RECEIPT',
                            request_digest=digest(envelope))
            if (type(receipt) is not dict or set(receipt) != {'record', 'signature'}
                    or canonical(receipt['record']) != canonical(expected)
                    or not valid_hex(receipt['signature'], 128)):
                return False
            Ed25519PublicKey.from_public_bytes(self.witness_public).verify(
                bytes.fromhex(receipt['signature']), canonical(expected))
            return True
        except (ValueError, TypeError, KeyError, UnicodeError, InvalidSignature):
            return False

    def _ledger(self):
        meta = self.db.execute('SELECT id, config, initial_digest FROM metadata').fetchall()
        if (len(meta) != 1 or meta[0][0] != 1
                or meta[0][1] != canonical(self.config).decode()
                or not valid_hex(meta[0][2], 64)):
            raise IntegrityError('Queue identity mismatch')
        sequence, head, last_digest, pending = 0, ZERO, meta[0][2], None
        try:
            for seq, raw_env, raw_receipt in self.db.execute(
                    'SELECT sequence, envelope, receipt FROM outbox ORDER BY sequence'):
                envelope = json.loads(raw_env)
                if (pending is not None or seq != sequence + 1
                        or canonical(envelope).decode() != raw_env
                        or not verify(envelope, {self.client_id: self.public})):
                    raise IntegrityError('Invalid queue request or sequence')
                req = envelope['request']
                if (req['store_id'] != self.store_id or req['sequence'] != seq
                        or req['generation'] != seq or req['previous_receipt_digest'] != head):
                    raise IntegrityError('Invalid request chain')
                if raw_receipt is None:
                    pending = envelope
                else:
                    receipt = json.loads(raw_receipt)
                    if canonical(receipt).decode() != raw_receipt or not self._valid_receipt(receipt, envelope):
                        raise IntegrityError('Invalid stored acknowledgment')
                    head = digest(receipt)
                sequence, last_digest = seq, req['state_digest']
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
            raise IntegrityError('Corrupt queue evidence') from exc
        return sequence, head, last_digest, pending

    def _rollback(self):
        try:
            self.db.rollback()
        except sqlite3.Error:
            pass

    def prepare(self):
        source = None
        try:
            self.db.execute('BEGIN IMMEDIATE')
            seq, head, last_digest, pending = self._ledger()
            source, state = self._source_snapshot()
            observed = _digest(state)
            if pending is not None:
                status = ('PENDING_ALREADY_DURABLE' if state['generation'] == seq
                          and observed == last_digest else 'SOURCE_PENDING_MISMATCH')
                return OutboxResult(status, envelope=pending if status == 'PENDING_ALREADY_DURABLE' else None)
            if state['generation'] == seq:
                return OutboxResult('NOTHING_TO_ATTEST' if observed == last_digest else 'SOURCE_DIGEST_MISMATCH')
            if state['generation'] != seq + 1:
                return OutboxResult('SOURCE_GENERATION_GAP_OR_ROLLBACK')
            req = dict(schema='F3-INT-121-A4-LOCAL', store_id=self.store_id,
                       sequence=seq + 1, generation=seq + 1, state_digest=observed,
                       previous_receipt_digest=head, nonce=secrets.token_hex(32))
            envelope = dict(request=req, key_id=self.client_id,
                            signature=self.private.sign(canonical(req)).hex())
            self.db.execute('INSERT INTO outbox VALUES (?, ?, NULL)',
                            (seq + 1, canonical(envelope).decode()))
            self._fault('after_prepare_insert')
            self.db.commit()
            self._fault('after_prepare_commit')
            return OutboxResult('PREPARED_DURABLE_LOCAL', envelope=envelope)
        except SourceError:
            return OutboxResult('SOURCE_UNAVAILABLE_OR_INVALID')
        except IntegrityError:
            return OutboxResult('QUEUE_INTEGRITY_ERROR')
        except sqlite3.Error:
            return OutboxResult('QUEUE_STORAGE_UNAVAILABLE')
        finally:
            self._rollback()
            if source is not None:
                source.close()

    def dispatch(self, submit):
        """Retry the persisted envelope; callback must not advance the source.

        Source snapshot stays open through witness commit and local ACK. This
        excludes ordinary DELETE-mode source writers only during this call.
        No atomic transaction across files or independent fencing is claimed.
        """
        source = None
        try:
            self.db.execute('BEGIN IMMEDIATE')
            seq, _, last_digest, pending = self._ledger()
            if pending is None:
                return OutboxResult('NOTHING_TO_DISPATCH')
            source, state = self._source_snapshot()
            if state['generation'] != seq or _digest(state) != last_digest:
                return OutboxResult('SOURCE_PENDING_MISMATCH')
            # Give the transport a detached object, retain the durable request.
            try:
                status, receipt = submit(json.loads(canonical(pending)))
                receipt = json.loads(canonical(receipt))
            except Exception:
                return OutboxResult('WITNESS_UNAVAILABLE_OR_UNCERTAIN')
            if status not in ('CONFIRMED', 'IDEMPOTENT_REPLAY'):
                return OutboxResult('WITNESS_REJECTED')
            if not self._valid_receipt(receipt, pending):
                return OutboxResult('INVALID_WITNESS_RECEIPT')
            self._fault('after_witness_ack')
            self.db.execute('UPDATE outbox SET receipt=? WHERE sequence=? AND receipt IS NULL',
                            (canonical(receipt).decode(), seq))
            self._fault('before_ack_commit')
            self.db.commit()
            self._fault('after_ack_commit')
            return OutboxResult('LOCAL_ATTESTATION_ACKNOWLEDGED', envelope=pending, receipt=receipt)
        except SourceError:
            return OutboxResult('SOURCE_UNAVAILABLE_OR_INVALID')
        except IntegrityError:
            return OutboxResult('QUEUE_INTEGRITY_ERROR')
        except sqlite3.Error:
            return OutboxResult('QUEUE_STORAGE_UNAVAILABLE')
        finally:
            self._rollback()
            if source is not None:
                source.close()

    def close(self):
        self.db.close()


def safe_to_promote(_result):
    return False
