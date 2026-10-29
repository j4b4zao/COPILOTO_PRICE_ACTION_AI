"""Offline isolated correction for false acknowledgments of SQLite UPDATE.

INT-109's state format and existing validation are reused unchanged. This facade
checks the affected row and reads back the complete next state inside the same
transaction before commit. It does not solve joint rollback, copied databases,
origin authentication, lost-ack reconciliation or hardware durability.
"""
import sqlite3
from tools import f3_int109_offline_consumption_store as prior


def _checkpoint(phase):
    """No-op seam for offline interruption tests, local to this facade."""


def consume_chain_confirmed(path, segments, *, expected_state_digest, expected_digest,
                            context, purpose, run_id, batches, base_registry=None):
    """Admit only a checked state transition; never repair or reset state.

    This entry point targets INT-109's pinned implementation/private helpers.
    SQLite's ordinary transaction and commit guarantees remain assumptions.
    An acknowledgment lost after commit still requires independent reconciliation.
    """
    if not prior.digest_valid(expected_state_digest):
        return prior.StoreResult('INVALID_STATE_ANCHOR')
    connection = None
    committed = False
    try:
        connection = prior._connect(path)
        connection.execute('BEGIN IMMEDIATE')
        state = prior._load(connection)
        if prior._digest(state) != expected_state_digest:
            return prior.StoreResult('STATE_ANCHOR_MISMATCH')
        if state['scope'] != [context, purpose, run_id]:
            return prior.StoreResult('STORE_SCOPE_MISMATCH')
        if state['next_revision'] > 2147483647:
            return prior.StoreResult('REVISION_DOMAIN_EXHAUSTED')
        result = prior.verify_typed_chain(
            segments, context=context, purpose=purpose, run_id=run_id,
            batches=batches, expected_digest=expected_digest,
            minimum_revision=state['next_revision'],
            consumed_chain_digests=frozenset(state['consumed']), base_registry=base_registry)
        if result.status != 'CHAIN_FIXTURE_UNAUTHENTICATED':
            return prior.StoreResult(result.status)
        if len(state['consumed']) >= 4096:
            return prior.StoreResult('HISTORY_CAPACITY_EXHAUSTED')
        next_state = dict(state, generation=state['generation']+1,
                          next_revision=batches[-1].revision+1,
                          consumed=sorted(state['consumed']+[result.digest]))
        _checkpoint('before_write')
        cursor = connection.execute('UPDATE state SET payload=? WHERE id=1', (prior._encode(next_state),))
        _checkpoint('after_write')
        if cursor.rowcount != 1:
            return prior.StoreResult('STATE_WRITE_NOT_CONFIRMED')
        # A trigger can restore OLD.payload while reporting one affected row.
        # Validate the complete readback, not just the count or a computed hash.
        if prior._load(connection) != next_state:
            return prior.StoreResult('STATE_WRITE_NOT_CONFIRMED')
        connection.commit()
        committed = True
        _checkpoint('after_commit')
        return prior.StoreResult('CONSUMED_FIXTURE_UNAUTHENTICATED', digest=result.digest,
                                 batch_digests=result.batch_digests,
                                 state_digest=prior._digest(next_state))
    except prior.SimulatedInterruption:
        return prior.StoreResult('COMMIT_OUTCOME_UNKNOWN' if committed else 'INTERRUPTED_ROLLED_BACK')
    except sqlite3.DatabaseError as error:
        return prior._db_error(error)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return prior.StoreResult('CORRUPT_STORE')
    except OSError:
        return prior.StoreResult('STORE_ERROR')
    finally:
        if connection is not None:
            connection.close()


def safe_to_promote(*args, **kwargs):
    return False
