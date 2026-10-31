"""Private startup-fault probes, always launched inside an outer safety Job.

No production API/status changes. Constructor objects retained here are private
test observations, not returned proofs from run_native_worker.
"""
import errno
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

MODES = ('create_failure','invalid_cwd','assign_failure','gate_failure',
         'target_crash','truncated_frame','handshake_timeout','journal_failure','success')


def exception(error, stage):
    return dict(type=type(error).__name__,message=str(error),stage=stage,observed_ns=time.perf_counter_ns(),
                errno=getattr(error,'errno',None),winerror=getattr(error,'winerror',None),
                is_os_error=isinstance(error,OSError))


def atomic_json(path, data):
    temporary=path.with_suffix('.pending')
    temporary.write_text(json.dumps(data),encoding='utf-8')
    temporary.replace(path)


def target(payload):
    root=Path(payload['root'])
    mode=payload['mode']
    atomic_json(root/'target-entered.json',dict(pid=os.getpid(),nonce=payload['nonce'],
        optimization=sys.flags.optimize,observed_ns=time.perf_counter_ns()))
    if mode=='target_crash':
        sys.stderr.write('A14_7_TARGET_STARTUP_CRASH\n')
        sys.stderr.flush()
        raise SystemExit(23)
    if mode=='truncated_frame':
        sys.stderr.write('A14_7_TARGET_TRUNCATED_FRAME\n')
        sys.stderr.flush()
        sys.stdout.write('{"nonce":')
        sys.stdout.flush()
        return
    if mode=='success':
        print(json.dumps(dict(schema='A14_7_READY',nonce=payload['nonce'],pid=os.getpid(),
                              optimization=sys.flags.optimize)),flush=True)
    deadline=time.monotonic()+30
    while not (root/'release-target').exists():
        if time.monotonic()>=deadline:
            raise TimeoutError('A14_7_TARGET_BARRIER_EXPIRED')
        time.sleep(0.02)


def probe(payload):
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools.f3_int115_process_identity import ProcessRef
    from f3_int121_a12_boundaries import _launcher
    from test_f3_int121_a12_boundaries import BoundaryTests
    root=Path(payload['root'])
    mode=payload['mode']
    created=[]
    primary=[]
    peer=control.Peer.__new__(control.Peer)
    original_popen=control.subprocess.Popen
    original_assign=control.Job.assign
    original_write=control.Peer._write
    def fail(kind,message,stage):
        error=kind(errno.EACCES if kind is PermissionError else errno.EPIPE,message)
        primary.append(exception(error,stage))
        raise error
    def spawn(*args,**kwargs):
        if mode in ('create_failure','journal_failure'):
            fail(PermissionError,'A14_7_INJECTED_PROCESS_CREATION','create_process')
        try:
            process=original_popen(*args,**kwargs)
        except OSError as error:
            primary.append(exception(error,'create_process'))
            raise
        ref=ProcessRef(process.pid)
        created.append(ref)
        return process
    def assign(job,process):
        if mode=='assign_failure':
            fail(PermissionError,'A14_7_INJECTED_ASSIGNMENT','assign_job')
        return original_assign(job,process)
    def write(subject,data):
        if mode=='gate_failure' and data==b'G':
            fail(BrokenPipeError,'A14_7_INJECTED_GATE_RELEASE','release_gate')
        return original_write(subject,data)
    stage='construct_peer'
    error=None
    received=None
    started=time.perf_counter_ns()
    try:
        with patch.object(control.subprocess,'Popen',side_effect=spawn), \
             patch.object(control.Job,'assign',new=assign), \
             patch.object(control.Peer,'_write',new=write):
            cwd=root/'nonexistent-working-directory' if mode=='invalid_cwd' else Path(__file__).resolve().parent
            control.Peer.__init__(peer,[sys.executable,'-B','-c',_launcher(__name__.replace('__main__','f3_int121_a14_7_startup_probe'),'--target')],
                                  cwd=cwd,timeout=8 if mode=='handshake_timeout' else 20)
            stage='send_payload'
            peer.send(json.dumps(payload))
            peer.process.stdin.close()
            stage='wait_target_entry'
            marker=BoundaryTests('test_death_before_source_commit').wait_json(root/'target-entered.json',timeout=5)
            if marker['nonce']!=payload['nonce'] or marker['optimization']!=sys.flags.optimize:
                raise ValueError('A14_7_TARGET_IDENTITY_MISMATCH')
            stage='recv_handshake'
            received=peer.recv()
            if received.get('schema')!='A14_7_READY' or received.get('nonce')!=payload['nonce'] or received.get('optimization')!=sys.flags.optimize:
                raise ValueError('A14_7_INVALID_HANDSHAKE')
            stage='handshake_validated'
    except BaseException as caught:
        error=exception(caught,stage)
    was_closed=peer.closed
    cleanup_started=time.perf_counter_ns()
    cleanup_error=None
    try:
        if not peer.closed:
            peer.close()
    except BaseException as caught:
        cleanup_error=exception(caught,'subject_cleanup')
    cleanup_finished=time.perf_counter_ns()
    direct=[]
    for ref in created:
        try:
            direct.append(dict(identity=ref.identity,exit_confirmed=ref.signalled(),proof='PINNED_HANDLE_SIGNALLED'))
        finally:
            ref.close()
    marker=None
    if (root/'target-entered.json').exists():
        marker=json.loads((root/'target-entered.json').read_bytes())
    result=dict(schema='A14_7_STARTUP_RECORD',mode=mode,nonce=payload['nonce'],probe_pid=os.getpid(),
        optimization=sys.flags.optimize,started_ns=started,cleanup_confirmation_started_ns=cleanup_started,
        cleanup_confirmation_finished_ns=cleanup_finished,observed_error=error,primary_errors=primary,
        detector_failure=exception(peer.failure,'detector') if peer.failure else None,
        subject_constructor_completed=stage!='construct_peer',subject_assigned=peer.assigned,
        subject_cleanup=peer.cleanup,subject_cleanup_error=cleanup_error,
        subject_job_handle_closed=peer.job.handle is None,subject_tracker_closed=peer.job.tracker.closed,
        subject_was_closed_before_confirmation=was_closed,
        subject_cleanup_scope='INNER_JOB_AND_DIRECT_LAUNCH_PROCESS_ONLY',
        full_subtree_exit_requires_outer_safety_proof=True,
        direct_processes=direct,target_entry=marker,received_frame=received,
        subject_stderr=bytes(peer.stderr).decode('utf-8',errors='replace'),
        journal_error=None,journal_written=False,f3='OPEN',offline=True,simulation_only=True,
        real_operations_authorized=False,runtime_modified=False,
        constructor_evidence_is_private=True,production_api_changed=False,
        controlled_injection=mode in ('create_failure','assign_failure','gate_failure','journal_failure'))
    result['journal_attempt_started_ns']=time.perf_counter_ns()
    try:
        path=root/'startup-journal.json'
        if mode=='journal_failure':
            blocked=root/'not-a-directory'
            blocked.write_text('private test fixture',encoding='utf-8')
            path=blocked/'startup-journal.json'
        result['journal_written']=True
        atomic_json(path,result)
    except OSError as caught:
        result['journal_written']=False
        result['journal_error']=exception(caught,'publish_after_cleanup')
        sys.stderr.write('A14_7_JOURNAL_PUBLISH_FAILED\n')
        sys.stderr.flush()
    # This fallback record is emitted only after cleanup, independently of
    # whether the specimen's own journal could be written.
    print(json.dumps(result),flush=True)
    deadline=time.monotonic()+40
    while not (root/'release-probe').exists():
        if time.monotonic()>=deadline:
            raise TimeoutError('A14_7_OBSERVER_DID_NOT_RELEASE_PROBE')
        time.sleep(0.02)


if __name__=='__main__':
    if os.name!='nt':
        raise RuntimeError('Native Windows startup probes required')
    payload=json.loads(sys.stdin.readline())
    if set(payload)!={'root','mode','nonce'} or payload['mode'] not in MODES:
        raise ValueError('Invalid private startup payload')
    if sys.argv[1:]==['--probe']:
        probe(payload)
    elif sys.argv[1:]==['--target']:
        target(payload)
    else:
        raise ValueError('Invalid startup entry point')
