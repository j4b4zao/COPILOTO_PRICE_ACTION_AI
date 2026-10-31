"""A12 controlled fault experiment: native owner death at writer/ACK seams.

Not an installed runtime path. All patches are private to spawned specimens;
historical source files stay unchanged. Never delete/rename a crash journal.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from f3_int121_a5_sqlite import SQLiteWitness, canonical, digest, valid_hex
from f3_int121_a9_route import OfflineConsumptionRoute, RouteResult
import f3_int121_a10_worker as worker_api
from f3_int121_a11_native import _wire, _unwire, MAX_FRAME

if os.name == 'nt':
    from a11_native.tools.f3_int115_process_control import Peer
else:
    Peer = None

PHASES = (
    'source:after_state_write', 'source:after_outbox_insert',
    'source:before_consumption_commit', 'source:after_consumption_commit',
    'witness:before_commit', 'witness:after_commit',
    'source:before_ack_commit', 'source:after_ack_commit',
)
_ORIGINAL_WORKER = worker_api._worker
_SPEC_ENV = 'F3_INT121_A12_SPECIMEN'


def recover_for_inquiry(path, *, config, client_private, before_state_digest, after_state_digest):
    """Explicit read/write OPEN for SQLite recovery, never consume or ACK.

    Independently retained pins constrain the observed result after opening.
    This is not a read-only forensic inspection or a new trust anchor.
    """
    if (not valid_hex(before_state_digest, 64) or not valid_hex(after_state_digest, 64)
            or before_state_digest == after_state_digest):
        return RouteResult('INVALID_RECONCILIATION_PIN')
    route = OfflineConsumptionRoute(path, config=config, client_private=client_private)
    def opened(store):
        state = store.state()
        if state['state_digest'] not in (before_state_digest, after_state_digest):
            return RouteResult('LOCAL_RECOVERY_UNRESOLVED')
        return RouteResult('LOCAL_OPEN_AND_PIN_MATCH_OBSERVED', state_digest=state['state_digest'],
                           snapshot=dict(generation=state['generation'], pending=state['pending'] is not None))
    return route._call(opened)


def _boundary_worker(*arguments):
    spec = json.loads(os.environ.pop(_SPEC_ENV))
    if set(spec) != {'root', 'phase'} or spec['phase'] not in PHASES:
        raise ValueError('Invalid private boundary specimen')
    root = Path(spec['root'])
    opened_sources = []
    fired = False
    original_open = OfflineConsumptionRoute._open
    original_witness_init = SQLiteWitness.__init__
    def pause(point, witness=None):
        nonlocal fired
        if point != spec['phase'] or fired:
            return
        fired = True
        record = dict(phase=point, worker_pid=os.getpid(), worker_parent_pid=os.getppid(),
                      optimization=sys.flags.optimize, reached_ns=time.perf_counter_ns(),
                      source_generation_seen=None, envelope_digest='', local_receipt_digest='',
                      witness_rows_seen=None)
        if opened_sources:
            connection = opened_sources[-1].db
            row = connection.execute('SELECT payload FROM state WHERE id=1').fetchone()
            record['source_generation_seen'] = json.loads(row[0])['generation']
            last = connection.execute('SELECT envelope, receipt FROM outbox ORDER BY sequence DESC LIMIT 1').fetchone()
            if last:
                record['envelope_digest'] = digest(json.loads(last[0]))
                if last[1] is not None:
                    record['local_receipt_digest'] = digest(json.loads(last[1]))
        if witness is not None:
            record['witness_rows_seen'] = witness.db.execute('SELECT count(*) FROM receipts').fetchone()[0]
        temporary = root / 'boundary.tmp'
        temporary.write_bytes(canonical(record))
        temporary.replace(root / 'boundary.json')
        deadline = time.monotonic() + 25
        while not (root / 'release-boundary').exists():
            if time.monotonic() > deadline:
                raise TimeoutError('Controlled boundary was not released')
            time.sleep(0.01)
    def source_open(route, **extra):
        store = original_open(route, **extra)
        opened_sources.append(store)
        store._fault = lambda point: pause('source:' + point)
        return store
    def witness_init(witness, *args, **kwargs):
        kwargs['_fault'] = lambda point: pause('witness:' + point, witness)
        original_witness_init(witness, *args, **kwargs)
    OfflineConsumptionRoute._open = source_open
    SQLiteWitness.__init__ = witness_init
    try:
        _ORIGINAL_WORKER(*arguments)
    finally:
        OfflineConsumptionRoute._open = original_open
        SQLiteWitness.__init__ = original_witness_init


def _read_payload():
    raw = sys.stdin.buffer.readline(MAX_FRAME + 1)
    if len(raw) > MAX_FRAME or not raw.endswith(b'\n'):
        raise ValueError('Invalid specimen frame')
    payload = _unwire(json.loads(raw))
    if (type(payload) is not dict or set(payload) !=
            {'root', 'phase', 'config', 'request', 'client_seed', 'witness_seed'}
            or payload['phase'] not in PHASES):
        raise ValueError('Invalid specimen payload')
    return payload


def _launcher(module, argument):
    options = ['-OO'] if sys.flags.optimize == 2 else (['-O'] if sys.flags.optimize else [])
    command = [sys.executable, '-B', *options, '-m', module, argument]
    return ('import os,subprocess,sys; env=dict(os.environ); env.pop("PYTHONOPTIMIZE",None); '
            'sys.exit(subprocess.run(' + repr(command) + ',env=env,close_fds=True,'
            'stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr,'
            'creationflags=subprocess.CREATE_NO_WINDOW).returncode)')


def _supervisor():
    payload = _read_payload()
    root = Path(payload['root'])
    peer = None
    try:
        peer = Peer([sys.executable, '-B', '-c', _launcher(__spec__.name, '--bridge')],
                    cwd=Path(__file__).resolve().parent, timeout=50)
        (root / 'controller.json').write_bytes(canonical(dict(owner_pid=os.getpid(), gate_pid=peer.pid)))
        peer.send(canonical(_wire(payload)).decode('utf-8'))
        peer.process.stdin.close()
        frame = peer.recv()
        peer.wait()
    finally:
        if peer is not None:
            peer.close()
    sys.stdout.buffer.write(canonical(dict(frame=frame, cleanup=peer.cleanup)) + b'\n')
    sys.stdout.buffer.flush()


def _bridge():
    payload = _read_payload()
    root = Path(payload['root'])
    (root / 'bridge.json').write_bytes(canonical(dict(bridge_pid=os.getpid(), optimization=sys.flags.optimize)))
    previous = os.environ.get(_SPEC_ENV)
    original = worker_api._worker
    os.environ[_SPEC_ENV] = json.dumps(dict(root=str(root), phase=payload['phase']))
    worker_api._worker = _boundary_worker
    try:
        result = worker_api.run_worker(root / 'route.sqlite', config=payload['config'],
            request=payload['request'],
            client_private=Ed25519PrivateKey.from_private_bytes(payload['client_seed']),
            witness_path=root / 'witness.sqlite',
            witness_private=Ed25519PrivateKey.from_private_bytes(payload['witness_seed']),
            timeout_seconds=40)
    finally:
        worker_api._worker = original
        if previous is None:
            os.environ.pop(_SPEC_ENV, None)
        else:
            os.environ[_SPEC_ENV] = previous
    sys.stdout.buffer.write(canonical(dict(schema='F3-INT-121-A12-RESULT',
        job_id=payload['request'].job_id, worker=asdict(result))) + b'\n')
    sys.stdout.buffer.flush()


def safe_to_promote(_result):
    return False


if __name__ == '__main__':
    if os.name != 'nt':
        raise SystemExit('Real Windows containment required')
    if sys.argv[1:] == ['--supervisor']:
        _supervisor()
    elif sys.argv[1:] == ['--bridge']:
        _bridge()
    else:
        raise SystemExit(64)
