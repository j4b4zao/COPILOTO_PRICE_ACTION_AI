"""A10: spawned offline callers of A9; no runtime installation or live orders.

Cleanup covers the directly owned worker. No Job Object, parent-death fencing,
independent custody or hard real-time bound is claimed. Keys cross local spawn
IPC in memory; this is a local test/service boundary, not secure key custody.
"""
from dataclasses import dataclass
import json
import math
import multiprocessing
from pathlib import Path
import re
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from f3_int121_a5_sqlite import SQLiteWitness, canonical, digest, public_bytes, valid_hex
from f3_int121_a9_route import (
    OfflineConsumptionRoute, RouteConfig, RouteResult, observe, reconcile,
)

MAX_REPLY = 4096
_STATUS = re.compile(r'[A-Z0-9_:.-]{1,128}\Z', re.ASCII)
_JOB_ID = re.compile(r'[A-Za-z0-9_.:-]{1,128}\Z', re.ASCII)
LOCKS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')


@dataclass(frozen=True)
class WorkRequest:
    job_id: str
    operation: str
    arguments: dict


@dataclass(frozen=True)
class WorkerResult(RouteResult):
    operation_status: str = ''
    reply: dict | None = None
    process_started: bool = False
    process_stopped: bool = True
    process_reaped: bool = False
    cleanup_confirmed: bool = True
    pid: int | None = None
    exit_code: int | None = None
    reason: str = ''


def resume_pending(route, *, pins, submit):
    """Explicit recovery only: inquiry and dispatch, NEVER another consumption.

    Observe a target after-state, then guard the actual envelope supplied under
    A8's write lock. A different later pending job must not reach the witness.
    """
    inquiry = reconcile(route.path, config=route.config, **pins)
    if inquiry.status == 'COMMITTED_ACKNOWLEDGED_OBSERVED_LOCAL':
        return RouteResult('ALREADY_ACKNOWLEDGED_LOCAL', state_digest=inquiry.state_digest)
    if inquiry.status != 'COMMITTED_PENDING_OBSERVED_LOCAL':
        return inquiry
    target = observe(route.path, config=route.config,
                     expected_state_digest=pins['after_state_digest'])
    if target.status != 'PENDING_OBSERVED_LOCAL':
        # Another caller may have acknowledged between the two snapshots.
        checked = reconcile(route.path, config=route.config, **pins)
        if checked.status == 'COMMITTED_ACKNOWLEDGED_OBSERVED_LOCAL':
            return RouteResult('ALREADY_ACKNOWLEDGED_LOCAL', state_digest=checked.state_digest)
        return RouteResult('RESUME_REQUIRES_NEW_INQUIRY')
    fingerprint = digest(target.snapshot['pending'])
    changed = False
    def guarded_submit(envelope):
        nonlocal changed
        if digest(envelope) != fingerprint:
            changed = True
            return 'TARGET_CHANGED', None
        return submit(envelope)
    result = route.dispatch(guarded_submit)
    if changed:
        return RouteResult('RESUME_TARGET_CHANGED')
    if result.status == 'NOTHING_TO_DISPATCH':
        checked = reconcile(route.path, config=route.config, **pins)
        if checked.status == 'COMMITTED_ACKNOWLEDGED_OBSERVED_LOCAL':
            return RouteResult('ALREADY_ACKNOWLEDGED_LOCAL', state_digest=checked.state_digest)
        return RouteResult('RESUME_REQUIRES_NEW_INQUIRY')
    return result


def _summary(job, result, error_type=''):
    envelope = getattr(result, 'envelope', None)
    receipt = getattr(result, 'receipt', None)
    return dict(schema='F3-INT-121-A10-RESULT', job_id=job.job_id,
                operation=job.operation, operation_status=result.status,
                state_digest=getattr(result, 'state_digest', '') or
                (envelope['request']['state_digest'] if envelope else ''),
                chain_digest=getattr(result, 'digest', ''),
                envelope_digest=digest(envelope) if envelope else '',
                receipt_digest=digest(receipt) if receipt else '',
                generation=envelope['request']['generation'] if envelope else None,
                error_type=error_type, **{name: False for name in LOCKS})


def _worker(send, database_path, config, job, client_seed, witness_path,
            witness_seed, test_mode):
    witness = None
    try:
        if test_mode == 'sleep_before_work':
            time.sleep(30)
        if test_mode == 'invalid_reply':
            send.send_bytes(b'not-json')
            return
        if job.operation == 'inquire':
            result = reconcile(database_path, config=config, **job.arguments)
        else:
            client = Ed25519PrivateKey.from_private_bytes(client_seed)
            route = OfflineConsumptionRoute(database_path, config=config,
                                            client_private=client, timeout=10)
            if job.operation == 'consume':
                arguments = dict(job.arguments)
                segments = arguments.pop('segments')
                result = route.consume_chain(segments, **arguments)
                if test_mode == 'exit_after_consume':
                    # Deterministic abrupt worker exit, after the route returned.
                    import os
                    os._exit(73)
            else:
                private = Ed25519PrivateKey.from_private_bytes(witness_seed)
                import hashlib
                trusted = {hashlib.sha256(config.client_public).hexdigest(): config.client_public}
                witness = SQLiteWitness(witness_path, config.store_id, private, trusted, timeout=10)
                def submit(envelope):
                    answer = witness.submit(envelope)
                    if test_mode == 'exit_after_witness_commit':
                        import os
                        os._exit(73)
                    if test_mode == 'lose_witness_ack':
                        raise TimeoutError('Injected local ACK loss')
                    return answer
                result = resume_pending(route, pins=job.arguments, submit=submit)
        reply = _summary(job, result)
    except Exception as exc:
        # Never serialize exception text, key material or raw task payloads.
        reply = _summary(job, RouteResult('WORKER_FAILED'), type(exc).__name__)
    finally:
        if witness is not None:
            witness.close()
    try:
        raw = canonical(reply)
        if len(raw) > MAX_REPLY:
            raw = canonical(_summary(job, RouteResult('REPLY_TOO_LARGE')))
        send.send_bytes(raw)
    finally:
        send.close()


def _validated_reply(raw, job):
    reply = json.loads(raw)
    fields = {'schema', 'job_id', 'operation', 'operation_status', 'state_digest',
              'chain_digest', 'envelope_digest', 'receipt_digest', 'generation', 'error_type', *LOCKS}
    if type(reply) is not dict or set(reply) != fields:
        raise ValueError('Invalid reply schema')
    if (reply['schema'] != 'F3-INT-121-A10-RESULT' or reply['job_id'] != job.job_id
            or reply['operation'] != job.operation or type(reply['operation_status']) is not str
            or not _STATUS.fullmatch(reply['operation_status'])
            or any(reply[name] is not False for name in LOCKS)):
        raise ValueError('Invalid reply context')
    for name in ('state_digest', 'chain_digest', 'envelope_digest', 'receipt_digest'):
        if reply[name] != '' and not valid_hex(reply[name], 64):
            raise ValueError('Invalid digest')
    generation = reply['generation']
    if generation is not None and (type(generation) is not int or not 1 <= generation <= 4096):
        raise ValueError('Invalid generation')
    if type(reply['error_type']) is not str or not re.fullmatch(r'[A-Za-z0-9_]{0,80}', reply['error_type']):
        raise ValueError('Invalid error summary')
    return reply


def run_worker(database_path, *, config, request, client_private=None,
               witness_path=None, witness_private=None, timeout_seconds=30,
               _test_mode=None):
    """Spawn one trusted-code worker; no shell, arbitrary executable or retry.

    A timeout/death means outcome UNKNOWN. Reconcile with retained pins using a
    separate inquire/resume request. Waiting and cleanup budgets are bounded
    locally; process startup and OS scheduling are not hard real-time guarantees.
    """
    try:
        if (not isinstance(config, RouteConfig) or not isinstance(request, WorkRequest)
                or type(request.job_id) is not str or not _JOB_ID.fullmatch(request.job_id)
                or request.operation not in ('consume', 'inquire', 'resume')
                or type(request.arguments) is not dict
                or type(timeout_seconds) not in (int, float)
                or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60
                or _test_mode not in (None, 'sleep_before_work', 'invalid_reply', 'exit_after_consume',
                                      'exit_after_witness_commit', 'lose_witness_ack')):
            raise ValueError('Invalid worker request')
        client_seed = witness_seed = None
        if request.operation != 'inquire':
            if public_bytes(client_private) != config.client_public:
                raise ValueError('Wrong client identity')
            client_seed = client_private.private_bytes(serialization.Encoding.Raw,
                                                       serialization.PrivateFormat.Raw,
                                                       serialization.NoEncryption())
        if request.operation == 'resume':
            if public_bytes(witness_private) != config.witness_public or witness_path is None:
                raise ValueError('Wrong witness identity')
            if Path(witness_path).resolve() == Path(database_path).resolve():
                raise ValueError('Witness must be a separate database')
            witness_seed = witness_private.private_bytes(serialization.Encoding.Raw,
                                                         serialization.PrivateFormat.Raw,
                                                         serialization.NoEncryption())
    except (ValueError, TypeError, AttributeError, OverflowError):
        return WorkerResult('REQUEST_REJECTED')
    receive = send = process = None
    started = False
    status, reason, reply = 'WORKER_OUTCOME_UNKNOWN', '', None
    stopped, reaped, exit_code, pid = True, False, None, None
    try:
        context = multiprocessing.get_context('spawn')
        receive, send = context.Pipe(duplex=False)
        process = context.Process(target=_worker, args=(send, str(database_path), config, request,
                                                        client_seed, str(witness_path), witness_seed, _test_mode))
        began = time.monotonic()
        process.start()
        started, pid = True, process.pid
        send.close()  # No extra parent writer handle may keep a partial frame open.
        while process.is_alive():
            remaining = timeout_seconds - (time.monotonic() - began)
            if remaining <= 0:
                reason = 'TIMEOUT'
                break
            process.join(min(0.05, remaining))
        if not process.is_alive():
            process.join()
            if process.exitcode != 0:
                reason = 'ABRUPT_EXIT'
            elif not receive.poll(0):
                reason = 'MISSING_REPLY'
            else:
                try:
                    # Worker has exited: closed writer gives EOF on a partial
                    # frame. Reply is intentionally small, not raw evidence.
                    reply = _validated_reply(receive.recv_bytes(MAX_REPLY), request)
                    status = 'WORKER_RETURNED'
                except (OSError, EOFError, ValueError, TypeError, UnicodeError):
                    reason = 'INVALID_REPLY'
    except Exception:
        reason = 'SUPERVISOR_ERROR' if started else 'START_FAILED'
    finally:
        # A start wrapper/interrupt can fail AFTER an OS process was launched.
        # Recover ownership from the Process handle before closing resources.
        if process is not None and not started and process.pid is not None:
            started, pid = True, process.pid
            reason = 'START_FAILED_AFTER_LAUNCH'
        if started:
            try:
                if process.is_alive():
                    process.terminate()
                    process.join(1.0)
            except OSError:
                pass  # Still attempt the stronger termination, then verify.
            try:
                if process.is_alive():
                    process.kill()
                    process.join(1.0)
            except OSError:
                pass  # An OS refusal must never become confirmed cleanup.
            stopped = not process.is_alive()
            exit_code = process.exitcode
            reaped = stopped and exit_code is not None
            if reaped:
                process.join(0)
        if receive is not None:
            receive.close()
        if send is not None:
            send.close()
        if process is not None and (not started or stopped):
            process.close()
    cleanup = not started or (stopped and reaped)
    if not cleanup:
        status, reason, reply = 'CLEANUP_INCONCLUSIVE', 'OWNED_WORKER_STILL_ACTIVE', None
    return WorkerResult(status, operation_status=reply['operation_status'] if reply else '',
                        reply=reply, process_started=started, process_stopped=stopped,
                        process_reaped=reaped, cleanup_confirmed=cleanup,
                        pid=pid, exit_code=exit_code, reason=reason)


def safe_to_promote(_result):
    return False
