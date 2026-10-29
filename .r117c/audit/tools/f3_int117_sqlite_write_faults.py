"""Disposable SQLite API-level experiments. No global patches or retry authority.

This is a separate offline writer using inherited canonical state/chain validators,
not instrumentation of consume_chain. Generated history entries are fixture data.
FULL is caused by page growth limits, READONLY by mode=ro, never Python-injected
database exceptions. Neither is evidence of power-loss resistance or custody.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from tools import f3_int109_offline_consumption_store as store
from tools.f3_int107_typed_batch_chain import build_typed_chain
from tools.f3_int108_typed_chain_guard import verify_typed_chain
from tools.f3_int114_custody_recovery import LOCKS
from tools.f3_int115_multiprocess_recovery import observe_recovery


class ProbeError(RuntimeError):
    """Missing evidence or unsafe experiment input; no successful observation."""


class _AdmissionRejected(Exception):
    def __init__(self, status):
        self.status = status


def reject(status):
    raise _AdmissionRejected(status)


def require(ok, message):
    if not ok:
        raise ProbeError(message)


def snapshot(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=rw', uri=True, timeout=0, isolation_level=None)
    try:
        connection.execute('BEGIN')
        integrity = connection.execute('PRAGMA integrity_check').fetchall()
        require(integrity == [('ok',)], 'SQLite integrity failed')
        state = store._load(connection)
        pages = connection.execute('PRAGMA page_count').fetchone()[0]
        return state, pages
    finally:
        connection.close()


def seed(path, state, page_size):
    # Only called for paths under this experiment's freshly created temp root.
    with path.open('xb'):
        pass
    connection = sqlite3.connect(path, timeout=0, isolation_level=None)
    try:
        connection.execute('PRAGMA page_size=' + str(page_size))
        require(connection.execute('PRAGMA page_size').fetchone()[0] == page_size, 'Page size not applied')
        require(connection.execute('PRAGMA journal_mode=DELETE').fetchone()[0] == 'delete', 'Journal not DELETE')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL)')
        connection.execute('INSERT INTO state VALUES(1, ?)', (store._encode(state),))
        connection.commit()
    finally:
        connection.close()


def growth_fixture(root, scope, previous_digest, next_digest, next_revision, page_size):
    """Prove growth on an independent identical control, not a byte-size guess."""
    for count in range(1, 65):
        history = sorted({previous_digest, *(hashlib.sha256(('synthetic-history-' + str(i)).encode()).hexdigest()
                                              for i in range(count))})
        require(next_digest not in history, 'Fixture digest collision')
        before = dict(version=1, generation=len(history), next_revision=next_revision,
                      scope=list(scope.values()), consumed=history)
        after = dict(before, generation=before['generation'] + 1, next_revision=next_revision + 1,
                     consumed=sorted(history + [next_digest]))
        original = root / ('seed' + str(count) + '.sqlite')
        control = root / ('control' + str(count) + '.sqlite')
        seed(original, before, page_size)
        require(snapshot(original)[0] == before, 'Seed state mismatch')
        shutil.copy2(original, control)
        control_before_hash = hashlib.sha256(control.read_bytes()).hexdigest()
        require(control_before_hash == hashlib.sha256(original.read_bytes()).hexdigest(), 'Control not byte-identical')
        old_pages = snapshot(control)[1]
        connection = store._connect(control)
        try:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('UPDATE state SET payload=? WHERE id=1', (store._encode(after),))
            connection.commit()
        finally:
            connection.close()
        persisted, new_pages = snapshot(control)
        require(persisted == after, 'Growth control state mismatch')
        if new_pages > old_pages:
            target = root / 'target.sqlite'
            shutil.copy2(original, target)
            require(hashlib.sha256(target.read_bytes()).hexdigest() == control_before_hash, 'Target not byte-identical to control input')
            return target, before, after, old_pages, new_pages
    raise ProbeError('No real page growth demonstrated; refusing to claim FULL coverage')


def write_once(path, mode, *, before, after, pins, segments, batches, scope,
               connection_observer=None):
    """One attempt on an explicitly owned connection. No patches or retries."""
    require(mode in ('normal', 'full', 'readonly'), 'Unsupported experiment mode')
    require(connection_observer is None or callable(connection_observer), 'Invalid connection observer')
    events = []
    connection = None
    phase = 'CONNECT'
    error_info = None
    committed = False
    status = 'STORE_ERROR'
    configuration = {}
    try:
        # Same pre-connection anchor gate as consume_chain.
        if not store.digest_valid(pins.get('before_state_digest')):
            reject('INVALID_STATE_ANCHOR')
        access = 'ro' if mode == 'readonly' else 'rw'
        connection = sqlite3.connect(path.resolve().as_uri() + '?mode=' + access,
                                     uri=True, timeout=0, isolation_level=None)
        events.append('connection_opened_' + access)
        if connection_observer is not None:
            connection_observer(connection)  # Explicit, connection-local test observer.
        phase = 'CONFIGURE'
        connection.execute('PRAGMA trusted_schema=OFF')
        require(connection.execute('PRAGMA journal_mode').fetchone()[0] == 'delete', 'Unexpected journal mode')
        connection.execute('PRAGMA synchronous=FULL')
        pages = connection.execute('PRAGMA page_count').fetchone()[0]
        page_size = connection.execute('PRAGMA page_size').fetchone()[0]
        if mode == 'full':
            effective = connection.execute('PRAGMA max_page_count=' + str(pages)).fetchone()[0]
            require(effective == pages and connection.execute('PRAGMA max_page_count').fetchone()[0] == pages,
                    'Limit not applied on writing connection')
        configuration = dict(access=access, page_count=pages, page_size=page_size,
            max_page_count=connection.execute('PRAGMA max_page_count').fetchone()[0],
            query_only=connection.execute('PRAGMA query_only').fetchone()[0],
            sqlite_version=sqlite3.sqlite_version,
            compile_options=[r[0] for r in connection.execute('PRAGMA compile_options')])
        phase = 'BEGIN_IMMEDIATE'
        events.append('begin_entered')
        connection.execute('BEGIN IMMEDIATE')
        phase = 'LOAD_AND_VALIDATE'
        current = store._load(connection)
        if store._digest(current) != pins['before_state_digest']:
            reject('STATE_ANCHOR_MISMATCH')
        if current['scope'] != [scope['context'], scope['purpose'], scope['run_id']]:
            reject('STORE_SCOPE_MISMATCH')
        if current['next_revision'] > 2147483647:
            reject('REVISION_DOMAIN_EXHAUSTED')
        require(current == before, 'Before-state fixture mismatch')
        checked = verify_typed_chain(segments, **scope, batches=batches,
            expected_digest=pins['expected_chain_digest'], minimum_revision=current['next_revision'],
            consumed_chain_digests=frozenset(current['consumed']))
        if checked.status != 'CHAIN_FIXTURE_UNAUTHENTICATED':
            reject(checked.status)
        events.append('chain_verified')
        # Preserve 109 order: anchor -> scope -> revision -> chain -> capacity
        # -> construct/check transition -> UPDATE -> COMMIT.
        events.append('capacity_checked')
        if len(current['consumed']) >= 4096:
            reject('HISTORY_CAPACITY_EXHAUSTED')
        require(after == dict(current, generation=current['generation'] + 1,
            next_revision=batches[-1].revision + 1, consumed=sorted(current['consumed'] + [checked.digest])),
            'After-state transition mismatch')
        phase = 'UPDATE'
        events.append('update_entered')
        connection.execute('UPDATE state SET payload=? WHERE id=1', (store._encode(after),))
        events.append('update_returned')
        phase = 'COMMIT'
        events.append('commit_entered')
        connection.commit()
        committed = True
        status = 'CONSUMED_FIXTURE_UNAUTHENTICATED'
        events.append('commit_returned')
    except _AdmissionRejected as rejection:
        status = rejection.status
        events.append('admission_rejected:' + status)
    except sqlite3.DatabaseError as error:
        code = getattr(error, 'sqlite_errorcode', None)
        require(type(code) is int, 'SQLite exception has no native result code')
        error_info = dict(phase=phase, sqlite_errorcode=code, primary_code=code & 255,
                          sqlite_errorname=getattr(error, 'sqlite_errorname', ''), message=str(error))
        events.append('sqlite_error_' + phase)
        status = store._db_error(error).status
    finally:
        if connection is not None:
            connection.close()
            events.append('connection_closed')
    return dict(status=status, committed=committed, error=error_info, events=events, configuration=configuration)


def validate_attempt(mode, attempt):
    require(mode in ('normal', 'full', 'readonly'), 'Unsupported experiment mode')
    require(attempt['events'] and attempt['events'][-1] == 'connection_closed', 'Connection cleanup unconfirmed')
    if mode == 'normal':
        require(attempt['committed'] is True and attempt['error'] is None and
                'commit_returned' in attempt['events'], 'Positive control did not commit')
    else:
        expected = sqlite3.SQLITE_FULL if mode == 'full' else sqlite3.SQLITE_READONLY
        error = attempt['error']
        require(error is not None and error['primary_code'] == expected and attempt['committed'] is False,
                'Expected native SQLite fault was not observed')
        require(error['phase'] in ('BEGIN_IMMEDIATE', 'UPDATE', 'COMMIT') and
                'sqlite_error_' + error['phase'] in attempt['events'], 'Fault phase evidence mismatch')
        require('commit_returned' not in attempt['events'], 'Unexpected commit after write fault')


def run_experiment(mode, *, segments, previous_batches, batches, scope, page_size=512,
                   writer=write_once):
    require(mode in ('normal', 'full', 'readonly'), 'Unsupported experiment mode')
    require(callable(writer), 'Invalid explicit experiment writer')
    require(type(page_size) is int and page_size in (512, 1024, 2048, 4096), 'Invalid fixture page size')
    require(type(scope) is dict and set(scope) == {'context', 'purpose', 'run_id'}, 'Invalid scope keys')
    scope = {key: scope[key] for key in ('context', 'purpose', 'run_id')}
    require(store._scope_valid(list(scope.values())), 'Invalid fixture scope')
    previous = build_typed_chain(segments, **scope, batches=previous_batches)
    proposed = build_typed_chain(segments, **scope, batches=batches)
    require(previous.status == proposed.status == 'CHAIN_FIXTURE_UNAUTHENTICATED', 'Invalid fixture chains')
    require(len(batches) == 1 and previous_batches[-1].revision + 1 == batches[0].revision,
            'Fixture requires the next single revision')
    result = dict(mode=mode, f3='OPEN', locks=dict.fromkeys(LOCKS, False), offline=True,
                  simulation_only=True, certification=False, retry_allowed=False, promoted=False)
    with tempfile.TemporaryDirectory(prefix='f117_') as directory:
        root = Path(directory)
        path, before, after, old_pages, new_pages = growth_fixture(root, scope, previous.digest,
            proposed.digest, batches[0].revision, page_size)
        pins = dict(before_state_digest=store._digest(before), after_state_digest=store._digest(after),
                    expected_chain_digest=proposed.digest, **scope)
        retained = json.dumps(pins, sort_keys=True).encode('ascii')
        reference = root / 'retained.json'
        reference.write_bytes(retained)
        file_before = hashlib.sha256(path.read_bytes()).hexdigest()
        attempt = writer(path, mode, before=before, after=after, pins=pins,
                         segments=segments, batches=batches, scope=scope)
        validate_attempt(mode, attempt)
        state, pages = snapshot(path)
        committed = mode == 'normal'
        require(state == (after if committed else before), 'Partial or unexpected persisted state')
        if not committed:
            require(hashlib.sha256(path.read_bytes()).hexdigest() == file_before, 'Failed write changed database bytes')
        reconciliation = observe_recovery(path, ack_state='UNKNOWN', **pins)
        expected = ('COMMITTED' if committed else 'NOT_COMMITTED') + '_OBSERVED_UNAUTHENTICATED'
        require(reconciliation.status == expected and reconciliation.retry_allowed is False, 'Reconciliation mismatch')
        older = dict(before, consumed=[], generation=0, next_revision=previous_batches[0].revision)
        replays = []
        for anchor in (store._digest(older), store._digest(state)):
            replay = store.consume_chain(path, segments, expected_state_digest=anchor,
                expected_digest=previous.digest, batches=previous_batches, **scope)
            replays.append(asdict(replay))
        require([x['status'] for x in replays] == ['STATE_ANCHOR_MISMATCH', 'STALE_CHAIN_REVISION'], 'Previously consumed replay admitted')
        if committed:
            for anchor, expected_status in ((pins['before_state_digest'], 'STATE_ANCHOR_MISMATCH'),
                                            (pins['after_state_digest'], 'STALE_CHAIN_REVISION')):
                replay = store.consume_chain(path, segments, expected_state_digest=anchor,
                    expected_digest=proposed.digest, batches=batches, **scope)
                require(replay.status == expected_status, 'Newly committed chain replay admitted')
                replays.append(asdict(replay))
        require(snapshot(path)[0] == state, 'Replay changed persisted state')
        wrong = dict(pins, before_state_digest='1' * 64, after_state_digest='2' * 64)
        unresolved = observe_recovery(path, **wrong)
        missing = observe_recovery(path, **dict(pins, before_state_digest=''))
        require(unresolved.status == 'RECONCILIATION_UNRESOLVED' and unresolved.retry_allowed is False,
                'Divergent anchors did not fail closed')
        require(missing.status == 'INVALID_RECONCILIATION_PIN' and missing.retry_allowed is False,
                'Missing anchor did not fail closed')
        for observation in (asdict(reconciliation), asdict(unresolved), asdict(missing), *replays):
            require(observation['f3'] == 'OPEN' and all(observation[k] is False for k in LOCKS), 'Unsafe inherited observation')
        require(reference.read_bytes() == retained, 'Retained anchors changed')
        result.update(attempt=attempt, growth_control=dict(pages_before=old_pages, pages_after=new_pages,
            before_digest=pins['before_state_digest'], after_digest=pins['after_state_digest'],
            synthetic_history_entries=len(before['consumed']), same_initial_bytes=True),
            integrity_check='ok', reopened_state=state, reopened_pages=pages,
            expected_before=before, expected_after=after, reconciliation=asdict(reconciliation),
            divergent_anchors=asdict(unresolved), missing_anchor=asdict(missing), replays=replays,
            database_unchanged_on_failure=not committed and hashlib.sha256(path.read_bytes()).hexdigest() == file_before,
            retained_sha256_before=hashlib.sha256(retained).hexdigest(),
            retained_sha256_after=hashlib.sha256(reference.read_bytes()).hexdigest(),
            fixture_directory=str(root), automatic_retries=0)
    require(not root.exists(), 'Disposable fixture cleanup failed')
    result['fixture_removed'] = True
    return result


def safe_to_promote(*args, **kwargs):
    return False
