"""A8: cooperative offline writer with state + outbox in ONE SQLite commit.

Not a distributed transaction, independent custody or a live trading adapter.
Legacy/direct SQL writers can bypass this API; divergence then fails closed.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3

from f3_int121_a5_sqlite import IntegrityError, canonical, public_bytes
from f3_int121_a7_outbox import AttestationOutbox, OutboxResult
from a6_vendor.tools import f3_int109_offline_consumption_store as legacy


@dataclass(frozen=True)
class AtomicResult(legacy.StoreResult):
    envelope: dict | None = None


class AtomicConsumptionStore(AttestationOutbox):
    """Reuses A7 signature/ledger verification; overrides all mutation paths.

    New database only for initialization. No migration or retroactive receipts.
    The witness callback is synchronous and must enforce its own timeout.
    One connection per caller/thread, as required by sqlite3.
    """
    def __init__(self, path, *, store_id, scope, client_private, witness_public,
                 create=False, minimum_revision=1, timeout=1.0, _fault=None):
        if type(store_id) is not str or not 0 < len(store_id) <= 128:
            raise ValueError('Invalid store identity')
        if type(scope) is not tuple or not legacy._scope_valid(list(scope)):
            raise ValueError('Invalid scope')
        if type(witness_public) is not bytes or len(witness_public) != 32:
            raise ValueError('Invalid witness public key')
        if type(minimum_revision) is not int or not 0 <= minimum_revision <= 2147483647:
            raise ValueError('Invalid minimum revision')
        self.path = self.source = Path(path).resolve()
        self.store_id, self.scope = store_id, scope
        self.private, self.public = client_private, public_bytes(client_private)
        self.client_id = hashlib.sha256(self.public).hexdigest()
        self.witness_public = witness_public
        self.config = dict(version=2, kind='A8_ATOMIC_LOCAL_STORE', store_id=store_id,
                           scope=list(scope), client_public=self.public.hex(),
                           witness_public=witness_public.hex())
        self._fault = _fault or (lambda stage: None)
        self.db = None
        if create:
            with self.path.open('xb'):
                pass
        try:
            self.db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True,
                                      isolation_level=None, timeout=timeout)
            self.db.execute('PRAGMA trusted_schema=OFF')
            self.db.execute('PRAGMA synchronous=FULL')
            if create:
                self.db.execute('PRAGMA journal_mode=DELETE')
            if self.db.execute('PRAGMA journal_mode').fetchone() != ('delete',):
                raise IntegrityError('Unsupported journal mode')
            if create:
                state = dict(version=1, generation=0, next_revision=minimum_revision,
                             scope=list(scope), consumed=[])
                self.db.execute('BEGIN IMMEDIATE')
                self.db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL)')
                self.db.execute('CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), config TEXT NOT NULL, initial_digest TEXT NOT NULL)')
                self.db.execute('CREATE TABLE outbox (sequence INTEGER PRIMARY KEY, envelope TEXT NOT NULL, receipt TEXT)')
                self.db.execute('INSERT INTO state VALUES (1, ?)', (legacy._encode(state),))
                self.db.execute('INSERT INTO metadata VALUES (1, ?, ?)',
                                (canonical(self.config).decode(), legacy._digest(state)))
                self._fault('before_initialization_commit')
                self.db.commit()
            self.db.execute('BEGIN')
            if self.db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise IntegrityError('SQLite quick_check failed')
            self._coherent()
            self.db.rollback()
        except BaseException:
            if self.db is not None:
                self.db.close()
            raise

    def _coherent(self):
        state = legacy._load(self.db)
        seq, head, last_digest, pending = self._ledger()
        if (state['scope'] != list(self.scope) or state['generation'] != seq
                or legacy._digest(state) != last_digest):
            raise IntegrityError('Source and outbox diverge')
        return state, seq, head, pending

    def state(self):
        self.db.execute('BEGIN')
        try:
            state, seq, head, pending = self._coherent()
            return dict(generation=state['generation'], sequence=seq, head=head,
                        state_digest=legacy._digest(state), pending=pending)
        finally:
            self._rollback()

    def prepare(self):
        # There is no post-commit preparation path in the A8 writer.
        return OutboxResult('PREPARATION_IS_ATOMIC_WITH_CONSUME')

    def consume(self, segments, *, expected_state_digest, expected_digest,
                context, purpose, run_id, batches, base_registry=None):
        if not legacy.digest_valid(expected_state_digest):
            return AtomicResult('INVALID_STATE_ANCHOR')
        commit_entered = False
        try:
            self.db.execute('BEGIN IMMEDIATE')
            state, seq, head, pending = self._coherent()
            # This additional gate precedes anchor/revision/chain checks. No next
            # generation may be admitted while the previous ACK is pending.
            if pending is not None:
                return AtomicResult('ATTESTATION_PENDING')
            if legacy._digest(state) != expected_state_digest:
                return AtomicResult('STATE_ANCHOR_MISMATCH')
            if state['scope'] != [context, purpose, run_id]:
                return AtomicResult('STORE_SCOPE_MISMATCH')
            if state['next_revision'] > 2147483647:
                return AtomicResult('REVISION_DOMAIN_EXHAUSTED')
            checked = legacy.verify_typed_chain(
                segments, context=context, purpose=purpose, run_id=run_id,
                batches=batches, expected_digest=expected_digest,
                minimum_revision=state['next_revision'],
                consumed_chain_digests=frozenset(state['consumed']),
                base_registry=base_registry)
            if checked.status != 'CHAIN_FIXTURE_UNAUTHENTICATED':
                return AtomicResult(checked.status)
            if len(state['consumed']) >= 4096:
                return AtomicResult('HISTORY_CAPACITY_EXHAUSTED')
            after = dict(state, generation=seq + 1,
                         next_revision=batches[-1].revision + 1,
                         consumed=sorted(state['consumed'] + [checked.digest]))
            state_digest = legacy._digest(after)
            request = dict(schema='F3-INT-121-A4-LOCAL', store_id=self.store_id,
                           sequence=seq + 1, generation=seq + 1,
                           state_digest=state_digest, previous_receipt_digest=head,
                           nonce=secrets.token_hex(32))
            envelope = dict(request=request, key_id=self.client_id,
                            signature=self.private.sign(canonical(request)).hex())
            self._fault('before_state_write')
            self.db.execute('UPDATE state SET payload=? WHERE id=1', (legacy._encode(after),))
            self._fault('after_state_write')
            self.db.execute('INSERT INTO outbox VALUES (?, ?, NULL)',
                            (seq + 1, canonical(envelope).decode()))
            self._fault('after_outbox_insert')
            self._coherent()
            self._fault('before_consumption_commit')
            commit_entered = True
            self.db.commit()
            self._fault('after_consumption_commit')
            return AtomicResult('CONSUMED_PENDING_ATTESTATION_LOCAL',
                                digest=checked.digest, batch_digests=checked.batch_digests,
                                state_digest=state_digest, envelope=envelope)
        except IntegrityError:
            return AtomicResult('ATTESTATION_STATE_MISMATCH')
        except legacy.SimulatedInterruption:
            return AtomicResult('COMMIT_OUTCOME_UNKNOWN' if commit_entered else 'INTERRUPTED_ROLLED_BACK')
        except sqlite3.Error as exc:
            if commit_entered:
                return AtomicResult('COMMIT_OUTCOME_UNKNOWN')
            return AtomicResult(legacy._db_error(exc).status)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return AtomicResult('CORRUPT_STORE')
        finally:
            self._rollback()

    def dispatch(self, submit):
        try:
            self.db.execute('BEGIN IMMEDIATE')
            _, seq, _, pending = self._coherent()
            if pending is None:
                return OutboxResult('NOTHING_TO_DISPATCH')
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
            if self._coherent()[3] is not None:
                raise IntegrityError('Acknowledgment was not persisted')
            self._fault('before_ack_commit')
            self.db.commit()
            self._fault('after_ack_commit')
            return OutboxResult('LOCAL_ATTESTATION_ACKNOWLEDGED', envelope=pending, receipt=receipt)
        except IntegrityError:
            return OutboxResult('ATTESTATION_STATE_MISMATCH')
        except sqlite3.Error:
            return OutboxResult('STORE_UNAVAILABLE_OR_ACK_UNCERTAIN')
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return OutboxResult('CORRUPT_STORE')
        finally:
            self._rollback()


def safe_to_promote(_result):
    return False
