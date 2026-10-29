"""F3-INT-110: fail-closed local outcome inquiry, NOT distributed commit.

The before/after digests must be pinned independently BEFORE inquiry. In
particular, a digest derived from the observed database is not a trust anchor.
The API cannot detect rollback of both SQLite and every independent anchor,
prove hardware durability, authenticate provenance, or deliver exactly once.
"""
from dataclasses import dataclass
from tools.f3_int109_offline_consumption_store import (_connect, _load, _digest,
    _db_error, StoreResult)
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid
import sqlite3


@dataclass(frozen=True)
class ReconciliationResult(StoreResult):
    """An observation only; all inherited operational locks stay false."""


def reconcile_consumption(path, *, before_state_digest, after_state_digest,
                          expected_chain_digest, context, purpose, run_id):
    """Classify a lost acknowledgment using *independently retained* pins.

    COMMITTED_OBSERVED: pinned after-state includes the expected chain.
    NOT_COMMITTED_OBSERVED: pinned before-state has not consumed the chain.
    Anything else is UNRESOLVED or a fail-closed error. Neither status is a
    durable delivery acknowledgment or permission to automatically retry.
    """
    if not all(digest_valid(d) for d in (before_state_digest, after_state_digest,
                                         expected_chain_digest)):
        return ReconciliationResult('INVALID_RECONCILIATION_PIN')
    if before_state_digest == after_state_digest:
        return ReconciliationResult('INVALID_RECONCILIATION_PIN')
    connection = None
    try:
        connection = _connect(path)
        connection.execute('BEGIN')
        state = _load(connection)
        if state['scope'] != [context, purpose, run_id]:
            return ReconciliationResult('STORE_SCOPE_MISMATCH')
        observed = _digest(state)
        consumed = expected_chain_digest in state['consumed']
        if observed == after_state_digest and consumed and state['generation'] >= 1:
            return ReconciliationResult('COMMITTED_OBSERVED_UNAUTHENTICATED',
                                        digest=expected_chain_digest, state_digest=observed)
        if observed == before_state_digest and not consumed:
            return ReconciliationResult('NOT_COMMITTED_OBSERVED_UNAUTHENTICATED',
                                        state_digest=observed)
        return ReconciliationResult('RECONCILIATION_UNRESOLVED')
    except sqlite3.DatabaseError as error:
        return ReconciliationResult(_db_error(error).status)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return ReconciliationResult('CORRUPT_STORE')
    except OSError:
        return ReconciliationResult('STORE_ERROR')
    finally:
        if connection is not None:
            connection.close()


def safe_to_promote(*args, **kwargs):
    return False
