"""A11: Windows Job boundary around A10/A9, with a gate before target code.

Only trusted typed local requests cross private stdin. No pickle, shell,
arbitrary executable, runtime installation or operational authorization.
"""
import base64
from dataclasses import asdict, dataclass, fields
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from f3_int121_a5_sqlite import canonical
from f3_int121_a9_route import RouteConfig, RouteResult
from f3_int121_a10_worker import WorkRequest, LOCKS, run_worker, _validated_reply
from a6_vendor.tools.f3_int98_policy_bundle_registry import (
    PolicyBundleRecord, PolicyEvidenceRegistry, PolicyEvidenceReceipt,
)
from a6_vendor.tools.f3_int101_cross_batch_audit import AuditSegment
from a6_vendor.tools.f3_int107_typed_batch_chain import ChainBatch
from a6_vendor.tools.f3_int106_typed_batch_manifest import TypedBatchEntry

if os.name == 'nt':
    from a11_native.tools.f3_int115_process_control import Peer
else:
    Peer = None

MAX_FRAME = 2 * 1024 * 1024
TYPES = {cls.__name__: cls for cls in (RouteConfig, WorkRequest, PolicyBundleRecord,
         PolicyEvidenceRegistry, PolicyEvidenceReceipt, AuditSegment, ChainBatch, TypedBatchEntry)}


@dataclass(frozen=True)
class NativeResult(RouteResult):
    worker_result: dict | None = None
    native_cleanup: dict | None = None
    assigned_before_target: bool = False
    cleanup_confirmed: bool = False
    bridge_optimization: int | None = None
    gate_pid: int | None = None
    error_type: str = ''


def _wire(value, depth=0):
    if depth > 64:
        raise ValueError('Wire depth exceeded')
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) is bytes:
        return {'kind': 'bytes', 'value': base64.b64encode(value).decode('ascii')}
    if type(value) in (tuple, list):
        return {'kind': 'tuple' if type(value) is tuple else 'list',
                'value': [_wire(v, depth + 1) for v in value]}
    if type(value) is dict and all(type(k) is str for k in value):
        return {'kind': 'dict', 'value': {k: _wire(v, depth + 1) for k, v in value.items()}}
    if type(value) in TYPES.values():
        return {'kind': type(value).__name__,
                'value': {f.name: _wire(getattr(value, f.name), depth + 1) for f in fields(value)}}
    raise ValueError('Unsupported local request type')


def _unwire(value, depth=0):
    if depth > 64:
        raise ValueError('Wire depth exceeded')
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) is not dict or set(value) != {'kind', 'value'}:
        raise ValueError('Invalid typed wire object')
    kind, payload = value['kind'], value['value']
    if kind == 'bytes' and type(payload) is str:
        return base64.b64decode(payload, validate=True)
    if kind in ('tuple', 'list') and type(payload) is list:
        decoded = [_unwire(v, depth + 1) for v in payload]
        return tuple(decoded) if kind == 'tuple' else decoded
    if kind == 'dict' and type(payload) is dict:
        return {k: _unwire(v, depth + 1) for k, v in payload.items()}
    if type(kind) is str and kind in TYPES and type(payload) is dict:
        cls = TYPES[kind]
        if set(payload) == {f.name for f in fields(cls)}:
            return cls(**{k: _unwire(v, depth + 1) for k, v in payload.items()})
    raise ValueError('Unknown typed wire object')


def _seed(private):
    if private is None:
        return None
    return private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                 serialization.NoEncryption())


def _bridge():
    try:
        raw = sys.stdin.buffer.readline(MAX_FRAME + 1)
        if not raw.endswith(b'\n') or len(raw) > MAX_FRAME:
            raise ValueError('Invalid input frame')
        payload = _unwire(json.loads(raw))
        expected = {'database_path', 'config', 'request', 'client_seed', 'witness_path',
                    'witness_seed', 'timeout_seconds', 'test_mode', 'marker_path', 'worker_test_mode'}
        if type(payload) is not dict or set(payload) != expected:
            raise ValueError('Invalid request context')
        specimen = payload['test_mode']
        if specimen is not None:
            if specimen not in ('hold_tree', 'root_exit_with_descendant'):
                raise ValueError('Unsupported specimen')
            child = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(30)'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
            with Path(payload['marker_path']).open('x', encoding='utf-8') as marker:
                json.dump(dict(gate_pid=os.getppid(), bridge_pid=os.getpid(), descendant_pid=child.pid), marker)
            if specimen == 'hold_tree':
                time.sleep(30)
            worker = None
        else:
            client = (Ed25519PrivateKey.from_private_bytes(payload['client_seed'])
                      if payload['client_seed'] is not None else None)
            witness = (Ed25519PrivateKey.from_private_bytes(payload['witness_seed'])
                       if payload['witness_seed'] is not None else None)
            worker = asdict(run_worker(payload['database_path'], config=payload['config'],
                request=payload['request'], client_private=client, witness_path=payload['witness_path'],
                witness_private=witness, timeout_seconds=payload['timeout_seconds'],
                _test_mode=payload['worker_test_mode']))
        frame = dict(schema='F3-INT-121-A11-RESULT', job_id=payload['request'].job_id,
                     optimization=sys.flags.optimize, specimen=specimen, worker=worker)
        sys.stdout.buffer.write(canonical(frame) + b'\n')
        sys.stdout.buffer.flush()
    except Exception as exc:
        # Do not expose private input or exception text through stderr.
        sys.stderr.write(type(exc).__name__ + '\n')
        raise SystemExit(72)


def run_native_worker(database_path, *, config, request, client_private=None,
                      witness_path=None, witness_private=None, timeout_seconds=20,
                      native_timeout_seconds=35, _test_mode=None, _marker_path=None,
                      _worker_test_mode=None):
    if os.name != 'nt':
        return NativeResult('WINDOWS_REQUIRED')
    peer = None
    error_type = ''
    worker = frame = None
    assigned, gate_pid, cleanup = False, None, None
    status = 'NATIVE_OUTCOME_UNKNOWN'
    try:
        if (not isinstance(config, RouteConfig) or not isinstance(request, WorkRequest)
                or type(native_timeout_seconds) not in (int, float)
                or not math.isfinite(native_timeout_seconds) or not 0 < native_timeout_seconds <= 120
                or type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                or not 0 < timeout_seconds <= 60
                or _test_mode not in (None, 'hold_tree', 'root_exit_with_descendant')
                or (_test_mode is not None and _marker_path is None)):
            raise ValueError('Invalid native request')
        payload = dict(database_path=str(database_path), config=config, request=request,
                       client_seed=_seed(client_private), witness_path=str(witness_path) if witness_path else None,
                       witness_seed=_seed(witness_private), timeout_seconds=timeout_seconds,
                       test_mode=_test_mode, marker_path=str(_marker_path) if _marker_path else None,
                       worker_test_mode=_worker_test_mode)
        encoded = canonical(_wire(payload))
        if len(encoded) + 1 > MAX_FRAME:
            raise ValueError('Input frame too large')
        options = ['-OO'] if sys.flags.optimize == 2 else (['-O'] if sys.flags.optimize else [])
        command = [sys.executable, '-B', *options, '-m', 'f3_int121_a11_native', '--bridge']
        # Fixed trusted launcher, current interpreter only; stdin is inherited
        # after the historical gate consumes its one-byte release token.
        launcher = ('import os,subprocess,sys; env=dict(os.environ); env.pop("PYTHONOPTIMIZE",None); '
                    'sys.exit(subprocess.run(' + repr(command) + ',env=env,close_fds=True,'
                    'stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr,'
                    'creationflags=subprocess.CREATE_NO_WINDOW).returncode)')
        peer = Peer([sys.executable, '-B', '-c', launcher],
                    cwd=Path(__file__).resolve().parent, timeout=native_timeout_seconds)
        assigned, gate_pid = peer.assigned, peer.pid
        peer.send(encoded.decode('utf-8'))
        peer.process.stdin.close()  # Exactly one request; never wait on input EOF.
        frame = peer.recv()
        code = peer.wait()
        if (code != 0 or type(frame) is not dict or set(frame) !=
                {'schema', 'job_id', 'optimization', 'specimen', 'worker'}
                or frame['schema'] != 'F3-INT-121-A11-RESULT'
                or frame['job_id'] != request.job_id
                or type(frame['optimization']) is not int or frame['optimization'] != sys.flags.optimize
                or frame['specimen'] != _test_mode):
            raise ValueError('Invalid native response')
        worker = frame['worker']
        if _test_mode is None:
            if (type(worker) is not dict or worker.get('status') not in
                    ('REQUEST_REJECTED', 'WORKER_RETURNED', 'WORKER_OUTCOME_UNKNOWN', 'CLEANUP_INCONCLUSIVE')
                    or any(worker.get(name) is not False for name in LOCKS) or worker.get('f3') != 'OPEN'):
                raise ValueError('Invalid worker result')
            if worker['status'] == 'WORKER_RETURNED':
                reply = _validated_reply(canonical(worker['reply']), request)
                if worker['operation_status'] != reply['operation_status']:
                    raise ValueError('Mismatched operation status')
            status = 'CONTAINED_WORKER_RETURNED'
        else:
            if worker is not None:
                raise ValueError('Invalid specimen response')
            status = 'NATIVE_SPECIMEN_COMPLETED'
    except Exception as exc:
        error_type = type(exc).__name__
        worker = None
    finally:
        if peer is not None:
            try:
                peer.close()
            except Exception as exc:
                error_type = error_type or type(exc).__name__
            cleanup = peer.cleanup
    confirmed = bool(cleanup and cleanup.get('confirmed') is True
                     and cleanup.get('active_processes') == 0
                     and cleanup.get('live_io_threads') == []
                     and cleanup.get('processes')
                     and all(p.get('exit_confirmed') is True for p in cleanup['processes']))
    if not confirmed:
        status, worker = 'NATIVE_CLEANUP_NOT_CONFIRMED', None
    return NativeResult(status, worker_result=worker, native_cleanup=cleanup,
                        assigned_before_target=assigned, cleanup_confirmed=confirmed,
                        bridge_optimization=frame.get('optimization') if type(frame) is dict else None,
                        gate_pid=gate_pid, error_type=error_type)


def safe_to_promote(_result):
    return False


if __name__ == '__main__':
    if sys.argv[1:] != ['--bridge']:
        raise SystemExit(64)
    _bridge()
