"""Local SQLite consumption fixture; not origin authentication or native fencing.

An independently retained state digest is mandatory. Restoring both database and
anchor defeats rollback detection. Commit and publication of that external anchor
are NOT one distributed transaction: an interrupted acknowledgment fails closed.
SQLite FULL/DELETE is a requested local durability configuration, not a hardware
power-loss guarantee. No live adapters, networking or orders exist here.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
from a6_vendor.tools.f3_int105_typed_identity_envelope import LABEL
from a6_vendor.tools.f3_int107_typed_batch_chain import ChainResult
from a6_vendor.tools.f3_int108_typed_chain_guard import verify_typed_chain
from a6_vendor.tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b'F3_INT109_LOCAL_CONSUMPTION_STATE_V1\0'
MAX_BYTES = 524288


@dataclass(frozen=True)
class StoreResult(ChainResult):
    state_digest: str = ''


class SimulatedInterruption(Exception):
    """Deterministic interruption used only by offline tests."""


def _checkpoint(phase):
    """No-op fault-injection seam; tests may interrupt or kill their own child."""


def _encode(state):
    return json.dumps(state, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _digest(state):
    return hashlib.sha256(DOMAIN + _encode(state)).hexdigest()


def _scope_valid(scope):
    return type(scope) is list and len(scope) == 3 and all(type(x) is str and LABEL.fullmatch(x) for x in scope)


def _load(connection):
    rows = connection.execute('SELECT id, length(payload), typeof(payload) FROM state LIMIT 2').fetchall()
    if len(rows) != 1 or rows[0][0] != 1 or rows[0][2] != 'blob' or not 1 <= rows[0][1] <= MAX_BYTES:
        raise ValueError('Invalid state row')
    raw = connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0]
    state = json.loads(raw.decode('ascii'))
    if type(state) is not dict or set(state) != {'version','generation','next_revision','scope','consumed'}:
        raise ValueError('Invalid state schema')
    if type(state['version']) is not int or state['version'] != 1:
        raise ValueError('Invalid version')
    consumed = state['consumed']
    if type(consumed) is not list or len(consumed) > 4096 or any(not digest_valid(x) for x in consumed):
        raise ValueError('Invalid consumption history')
    if consumed != sorted(set(consumed)):
        raise ValueError('History is not canonical and unique')
    if type(state['generation']) is not int or state['generation'] != len(consumed):
        raise ValueError('Invalid generation')
    if type(state['next_revision']) is not int or not 0 <= state['next_revision'] <= 2147483648:
        raise ValueError('Invalid revision floor')
    if not _scope_valid(state['scope']) or raw != _encode(state):
        raise ValueError('Noncanonical state')
    return state


def _connect(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=rw', uri=True, timeout=0, isolation_level=None)
    try:
        connection.execute('PRAGMA trusted_schema=OFF')
        mode = connection.execute('PRAGMA journal_mode').fetchone()[0]
        if mode != 'delete':
            raise ValueError('Unsupported journal mode')
        connection.execute('PRAGMA synchronous=FULL')
        return connection
    except BaseException:
        connection.close()
        raise


def _db_error(error):
    code = getattr(error, 'sqlite_errorcode', 0) & 255
    return StoreResult('STORE_BUSY' if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) else 'STORE_ERROR')


def create_store(path, *, context, purpose, run_id, minimum_revision):
    """Explicit first initialization only. Existing or missing parents never reset.

    The returned state digest must be retained independently by the caller.
    A failed initialization leaves an unusable fixture; no fallback is attempted.
    """
    scope = [context, purpose, run_id]
    if not _scope_valid(scope) or type(minimum_revision) is not int or not 0 <= minimum_revision <= 2147483647:
        return StoreResult('INVALID_INITIAL_STATE')
    state = dict(version=1,generation=0,next_revision=minimum_revision,scope=scope,consumed=[])
    connection = None
    try:
        with Path(path).open('xb'):
            pass
        connection = sqlite3.connect(path, timeout=0, isolation_level=None)
        connection.execute('PRAGMA journal_mode=DELETE')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL)')
        connection.execute('INSERT INTO state VALUES (1, ?)', (_encode(state),))
        connection.commit()
        return StoreResult('STORE_FIXTURE_UNAUTHENTICATED',state_digest=_digest(state))
    except FileExistsError:
        return StoreResult('STORE_EXISTS')
    except sqlite3.DatabaseError as error:
        return _db_error(error)
    except OSError:
        return StoreResult('STORE_ERROR')
    finally:
        if connection is not None:
            connection.close()


def verify_store(path, *, expected_state_digest):
    """Verify persisted bytes against an independent anchor without reinitializing."""
    if not digest_valid(expected_state_digest):
        return StoreResult('INVALID_STATE_ANCHOR')
    connection = None
    try:
        connection = _connect(path)
        connection.execute('BEGIN')
        state = _load(connection)
        if _digest(state) != expected_state_digest:
            return StoreResult('STATE_ANCHOR_MISMATCH')
        return StoreResult('STORE_FIXTURE_UNAUTHENTICATED',state_digest=expected_state_digest)
    except sqlite3.DatabaseError as error:
        return _db_error(error)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return StoreResult('CORRUPT_STORE')
    except OSError:
        return StoreResult('STORE_ERROR')
    finally:
        if connection is not None:
            connection.close()


def consume_chain(path, segments, *, expected_state_digest, expected_digest,
                  context, purpose, run_id, batches, base_registry=None):
    """Serialize check+consume+floor update in a single SQLite transaction.

    A stale external anchor cannot win a second admission. Busy is a rejection,
    never a reset. On COMMIT_OUTCOME_UNKNOWN, the caller must not report success
    or retry with fabricated state; independent reconciliation is outside scope.
    """
    if not digest_valid(expected_state_digest):
        return StoreResult('INVALID_STATE_ANCHOR')
    connection = None
    committed = False
    try:
        connection = _connect(path)
        connection.execute('BEGIN IMMEDIATE')
        state = _load(connection)
        if _digest(state) != expected_state_digest:
            return StoreResult('STATE_ANCHOR_MISMATCH')
        if state['scope'] != [context, purpose, run_id]:
            return StoreResult('STORE_SCOPE_MISMATCH')
        if state['next_revision'] > 2147483647:
            return StoreResult('REVISION_DOMAIN_EXHAUSTED')
        result = verify_typed_chain(segments,context=context,purpose=purpose,run_id=run_id,
                                    batches=batches,expected_digest=expected_digest,
                                    minimum_revision=state['next_revision'],
                                    consumed_chain_digests=frozenset(state['consumed']),
                                    base_registry=base_registry)
        if result.status != 'CHAIN_FIXTURE_UNAUTHENTICATED':
            return StoreResult(result.status)
        if len(state['consumed']) >= 4096:
            return StoreResult('HISTORY_CAPACITY_EXHAUSTED')
        new_state = dict(state, generation=state['generation']+1,
                         next_revision=batches[-1].revision+1,
                         consumed=sorted(state['consumed']+[result.digest]))
        _checkpoint('before_write')
        connection.execute('UPDATE state SET payload=? WHERE id=1', (_encode(new_state),))
        _checkpoint('after_write')
        connection.commit()
        committed = True
        _checkpoint('after_commit')
        return StoreResult('CONSUMED_FIXTURE_UNAUTHENTICATED',digest=result.digest,
                           batch_digests=result.batch_digests,state_digest=_digest(new_state))
    except SimulatedInterruption:
        return StoreResult('COMMIT_OUTCOME_UNKNOWN' if committed else 'INTERRUPTED_ROLLED_BACK')
    except sqlite3.DatabaseError as error:
        # Commit failure may require reopening and checking the retained anchor.
        # Never turn a database error into a successful consumption.
        return _db_error(error)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return StoreResult('CORRUPT_STORE')
    except OSError:
        return StoreResult('STORE_ERROR')
    finally:
        if connection is not None:
            connection.close()


def safe_to_promote(*args, **kwargs):
    return False
