"""Private Windows Job/barrier specimens. No SQLite or operational I/O.

The deliberately uncontained inner Job exists only in this executable test
process. Every specimen must already be inside the observer's outer safety Job.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

MODULE = 'f3_int121_a14_6_specimen'


def publish(root, name, **fields):
    path = root / name
    temporary = root / (name + '.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(dict(pid=os.getpid(), optimization=sys.flags.optimize,
                                       observed_ns=time.perf_counter_ns(), **fields)), encoding='utf-8')
    temporary.replace(path)


def wait_release(root, name, deadline):
    while not (root / name).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('A14_6_SPECIMEN_BARRIER_EXPIRED: ' + name)
        time.sleep(0.02)


def leaf(role, root, nonce):
    deadline = time.monotonic() + 60
    publish(root, role + '-ready.json', nonce=nonce, role=role)
    if role == 'held':
        # This handshake and the retention barrier do not use the worker's
        # stdin/stdout/stderr and do not observe worker or owner liveness.
        wait_release(root, 'ack-held.json', deadline)
        ack = json.loads((root / 'ack-held.json').read_bytes())
        if ack != {'nonce': nonce}:
            raise ValueError('A14_6_BAD_HANDSHAKE_NONCE')
        publish(root, 'held-ack.json', nonce=nonce, state='HELD')
    wait_release(root, 'release-' + role, deadline)


def host(payload):
    root, nonce = Path(payload['root']), payload['nonce']
    options = ['-O'] if sys.flags.optimize else []
    children = []
    for role in ('worker', 'held'):
        children.append(subprocess.Popen(
            [sys.executable, '-B', *options, str(Path(__file__).resolve()),
             '--leaf', role, str(root), nonce],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW))
    publish(root, 'host.json', nonce=nonce, child_launch_pids=[p.pid for p in children])
    try:
        wait_release(root, 'release-host', time.monotonic() + 75)
    finally:
        # Observer safety containment remains mandatory if this cleanup fails.
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)


def owner(payload):
    from a11_native.tools import f3_int115_process_control as control
    from f3_int121_a12_boundaries import _launcher
    root = Path(payload['root'])
    inner = None
    try:
        inner = control.Peer([sys.executable, '-B', '-c', _launcher(MODULE, '--host')],
                             cwd=Path(__file__).resolve().parent, timeout=90)
        flags = 0 if payload['negative'] else 0x2000
        limits = control.ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = flags
        # Only this process's private inner Job is changed; the observer's
        # outer Job is never supplied here or modified. The host blocks on its
        # input frame until the intended inner-Job mode has been established.
        control.wincheck(control.K.SetInformationJobObject(
            inner.job.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        inner.send(json.dumps(payload))
        inner.process.stdin.close()
        publish(root, 'owner.json', nonce=payload['nonce'], inner_job_limit_flags=flags,
                negative_control=payload['negative'])
        wait_release(root, 'release-owner', time.monotonic() + 80)
    finally:
        if inner is not None:
            inner.close()


if __name__ == '__main__':
    if os.name != 'nt':
        raise RuntimeError('Native Windows Job specimens required')
    if sys.argv[1:2] == ['--leaf']:
        _, role, directory, nonce = sys.argv[1:]
        if role not in ('worker', 'held'):
            raise ValueError('Invalid leaf role')
        leaf(role, Path(directory), nonce)
    else:
        payload = json.loads(sys.stdin.readline())
        if set(payload) != {'root', 'nonce', 'negative'} or type(payload['negative']) is not bool:
            raise ValueError('Invalid private A14.6 payload')
        if sys.argv[1:] == ['--owner']:
            owner(payload)
        elif sys.argv[1:] == ['--host']:
            host(payload)
        else:
            raise ValueError('Invalid specimen entry point')
