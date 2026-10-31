"""A9 offline route: A8 only, explicit empty-store copy, pinned outcome inquiry.

No runtime cutover, legacy write fallback, network setup or live authorization.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3

from f3_int121_a5_sqlite import IntegrityError, public_bytes
from f3_int121_a7_outbox import AttestationOutbox
from f3_int121_a8_atomic_store import AtomicConsumptionStore
from a6_vendor.tools import f3_int109_offline_consumption_store as legacy


@dataclass(frozen=True)
class RouteConfig:
    store_id: str
    scope: tuple
    client_public: bytes
    witness_public: bytes

    def __post_init__(self):
        if type(self.store_id) is not str or not 0 < len(self.store_id) <= 128:
            raise ValueError('Invalid store identity')
        if type(self.scope) is not tuple or not legacy._scope_valid(list(self.scope)):
            raise ValueError('Invalid scope')
        if any(type(key) is not bytes or len(key) != 32
               for key in (self.client_public, self.witness_public)):
            raise ValueError('Invalid pinned public key')

    def metadata(self):
        return dict(version=2, kind='A8_ATOMIC_LOCAL_STORE', store_id=self.store_id,
                    scope=list(self.scope), client_public=self.client_public.hex(),
                    witness_public=self.witness_public.hex())


@dataclass(frozen=True)
class RouteResult(legacy.StoreResult):
    snapshot: dict | None = None


class _ReadLedger(AttestationOutbox):
    """Signature verifier only; connection is supplied in query-only mode."""
    def __init__(self, connection, config):
        self.db, self.config = connection, config.metadata()
        self.public = config.client_public
        self.client_id = hashlib.sha256(self.public).hexdigest()
        self.store_id, self.scope = config.store_id, config.scope
        self.witness_public = config.witness_public


def _read_connection(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Not a database file')
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True,
                           isolation_level=None, timeout=0)
    try:
        conn.execute('PRAGMA trusted_schema=OFF')
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        if conn.execute('PRAGMA journal_mode').fetchone() != ('delete',):
            raise ValueError('Unsupported journal mode')
        return conn
    except BaseException:
        conn.close()
        raise


def _snapshot(path, config):
    conn = _read_connection(path)
    try:
        state = legacy._load(conn)
        seq, head, anchor, pending = _ReadLedger(conn, config)._ledger()
        if (state['scope'] != list(config.scope) or state['generation'] != seq
                or legacy._digest(state) != anchor):
            raise IntegrityError('Source and attestation ledger diverge')
        return dict(generation=seq, observed_state_digest=anchor, head=head,
                    pending=pending, consumed=tuple(state['consumed']))
    finally:
        conn.close()


def observe(path, *, config, expected_state_digest):
    """Read-only comparison against a caller-retained pin; not a new anchor."""
    if not isinstance(config, RouteConfig):
        return RouteResult('INVALID_ROUTE_CONFIG')
    if not legacy.digest_valid(expected_state_digest):
        return RouteResult('INVALID_STATE_ANCHOR')
    try:
        snapshot = _snapshot(path, config)
        if snapshot['observed_state_digest'] != expected_state_digest:
            return RouteResult('STATE_ANCHOR_MISMATCH')
        return RouteResult('PENDING_OBSERVED_LOCAL' if snapshot['pending'] else 'ACKNOWLEDGED_OR_INITIAL_LOCAL',
                           state_digest=expected_state_digest, snapshot=snapshot)
    except FileNotFoundError:
        return RouteResult('DATABASE_NOT_FOUND')
    except (IntegrityError, ValueError, TypeError, UnicodeError, RecursionError):
        return RouteResult('DATABASE_FORMAT_OR_IDENTITY_REJECTED')
    except (OSError, sqlite3.Error):
        return RouteResult('DATABASE_UNAVAILABLE_OR_INVALID')


def reconcile(path, *, config, before_state_digest, after_state_digest,
              expected_chain_digest):
    """Pins MUST be retained independently before inquiry, as in F3-INT-110.

    No automatic retry, receipt fabrication or anchor replacement occurs.
    Joint rollback of all pins and local databases remains outside this proof.
    """
    if not isinstance(config, RouteConfig):
        return RouteResult('INVALID_ROUTE_CONFIG')
    if (not all(legacy.digest_valid(p) for p in
                (before_state_digest, after_state_digest, expected_chain_digest))
            or before_state_digest == after_state_digest):
        return RouteResult('INVALID_RECONCILIATION_PIN')
    try:
        snapshot = _snapshot(path, config)
        observed = snapshot['observed_state_digest']
        consumed = expected_chain_digest in snapshot['consumed']
        if observed == before_state_digest and not consumed:
            return RouteResult('NOT_COMMITTED_OBSERVED_LOCAL', state_digest=before_state_digest)
        if observed == after_state_digest and consumed:
            return RouteResult('COMMITTED_PENDING_OBSERVED_LOCAL' if snapshot['pending']
                               else 'COMMITTED_ACKNOWLEDGED_OBSERVED_LOCAL',
                               state_digest=after_state_digest, digest=expected_chain_digest)
        return RouteResult('RECONCILIATION_UNRESOLVED')
    except FileNotFoundError:
        return RouteResult('DATABASE_NOT_FOUND')
    except (IntegrityError, ValueError, TypeError, UnicodeError, RecursionError):
        return RouteResult('DATABASE_FORMAT_OR_IDENTITY_REJECTED')
    except (OSError, sqlite3.Error):
        return RouteResult('DATABASE_UNAVAILABLE_OR_INVALID')


class OfflineConsumptionRoute:
    """Single explicit route. Open errors never call legacy.consume_chain.

    Each operation owns and closes its A8 connection. This route does not
    silently install itself into the application or retire other writers.
    """
    def __init__(self, path, *, config, client_private, timeout=1.0):
        if not isinstance(config, RouteConfig):
            raise ValueError('Invalid route configuration')
        if public_bytes(client_private) != config.client_public:
            raise ValueError('Client signing identity does not match pinned configuration')
        self.path, self.config = Path(path).resolve(), config
        self.private, self.timeout = client_private, timeout

    def _open(self, **extra):
        return AtomicConsumptionStore(
            self.path, store_id=self.config.store_id, scope=self.config.scope,
            client_private=self.private, witness_public=self.config.witness_public,
            timeout=self.timeout, **extra)

    def _call(self, operation, *, create=False, minimum_revision=1):
        store = None
        try:
            store = self._open(create=create, minimum_revision=minimum_revision)
            return operation(store)
        except FileExistsError:
            return RouteResult('DATABASE_EXISTS')
        except FileNotFoundError:
            return RouteResult('DATABASE_NOT_FOUND')
        except (IntegrityError, ValueError, TypeError, UnicodeError, RecursionError):
            return RouteResult('DATABASE_FORMAT_OR_IDENTITY_REJECTED')
        except (OSError, sqlite3.Error):
            # Existing incompatible schemas and absent mode=rw files both fail
            # here, without a creation or legacy-consumption fallback.
            return RouteResult('DATABASE_UNAVAILABLE_OR_INVALID')
        finally:
            if store is not None:
                store.close()

    def create_new(self, *, minimum_revision=1):
        return self._call(lambda s: RouteResult('INITIALIZED_LOCAL',
                                               state_digest=s.state()['state_digest']),
                          create=True, minimum_revision=minimum_revision)

    def consume_chain(self, segments, **arguments):
        return self._call(lambda s: s.consume(segments, **arguments))

    def dispatch(self, submit):
        return self._call(lambda s: s.dispatch(submit))

    def copy_empty_legacy(self, source_path, *, expected_state_digest):
        """Explicit snapshot copy to a NEW A8 destination; no source cutover.

        Only a pristine state-only generation-zero database is supported.
        Source read lock spans destination initialization. Old source remains
        intact and must be retired separately before any actual integration.
        """
        if not legacy.digest_valid(expected_state_digest):
            return RouteResult('INVALID_STATE_ANCHOR')
        conn = None
        try:
            source = Path(source_path).resolve(strict=True)
            if source == self.path:
                return RouteResult('MIGRATION_REQUIRES_NEW_DESTINATION')
            conn = _read_connection(source)
            objects = conn.execute("SELECT type, name FROM sqlite_master WHERE name NOT GLOB 'sqlite_*'").fetchall()
            if objects != [('table', 'state')]:
                return RouteResult('MIGRATION_SOURCE_NOT_LEGACY_STATE_ONLY')
            state = legacy._load(conn)
            if state['scope'] != list(self.config.scope):
                return RouteResult('STORE_SCOPE_MISMATCH')
            if legacy._digest(state) != expected_state_digest:
                return RouteResult('STATE_ANCHOR_MISMATCH')
            if state['generation'] != 0:
                return RouteResult('MIGRATION_HISTORY_REQUIRES_SEPARATE_PROCEDURE')
            if state['next_revision'] > 2147483647:
                return RouteResult('REVISION_DOMAIN_EXHAUSTED')
            created = self.create_new(minimum_revision=state['next_revision'])
            if created.status != 'INITIALIZED_LOCAL':
                return created
            if created.state_digest != expected_state_digest:
                return RouteResult('MIGRATION_COPY_MISMATCH')
            return RouteResult('EMPTY_LEGACY_COPIED_LOCAL', state_digest=expected_state_digest)
        except FileNotFoundError:
            return RouteResult('DATABASE_NOT_FOUND')
        except (IntegrityError, ValueError, TypeError, UnicodeError, RecursionError):
            return RouteResult('DATABASE_FORMAT_OR_IDENTITY_REJECTED')
        except (OSError, sqlite3.Error):
            return RouteResult('DATABASE_UNAVAILABLE_OR_INVALID')
        finally:
            if conn is not None:
                conn.close()


def safe_to_promote(_result):
    return False
