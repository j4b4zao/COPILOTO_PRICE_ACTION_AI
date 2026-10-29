"""X2 offline supervisor. No production adapter or executable live entry point.

Factories are trusted synthetic test code, not a security sandbox. A future
adapter must bind exclusively to already open Excel/workbook handles and own
neither their lifecycle nor saving. No connection implementation is supplied.
Only bounded, validated observational projections cross the process boundary.
"""
import json
import functools
import importlib
import queue
import subprocess
import threading
import types
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol

from market_data.source_acquisition_observational_report import (
    ObservationalReport, to_observational_dict,
)


@dataclass(frozen=True)
class SessionPolicy:
    symbol: str = 'WINZ26'
    mode: str = 'NORMAL'
    max_attempts: int = 20
    duration: float = 60
    interval: float = 2
    cycle_timeout: float = 5
    retention: int = 20
    snapshot: bool = False
    rtd_order_flow: bool = False
    persistence: bool = False
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False

    def __post_init__(self):
        import math
        if self.symbol != 'WINZ26' or self.mode != 'NORMAL':
            raise ValueError('INVALID_POLICY')
        for name, low, high in (('max_attempts', 1, 20), ('retention', 1, 20)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError('INVALID_POLICY')
        for name, low, high in (('duration', 0, 60), ('interval', 2, 60),
                                ('cycle_timeout', 0, 5)):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high or value == 0:
                raise ValueError('INVALID_POLICY')
        if any(getattr(self, n) is not False for n in (
                'snapshot', 'rtd_order_flow', 'persistence', 'orders_allowed',
                'live_certified', 'flow_complete')):
            raise ValueError('INVALID_POLICY')


class OfflineAdapter(Protocol):
    """One call consumes exactly one existing collection cycle, no reread.

    Must return its already published report; discard market return values.
    close() releases adapter resources only, never operator applications/files.
    Implementations must honor all policy flags. X2 accepts synthetic factories.
    """
    def collect_once(self, cycle_id: int) -> ObservationalReport: ...
    def close(self) -> None: ...


class ExistingOpenBinding(Protocol):
    """Future binding only; X2 supplies no implementation or real invocation.

    Both handles must already exist. Implementers must reject missing handles,
    never launch Excel, open workbooks, save, close, or read for confirmation.
    The factory must create/bind its adapter inside the supervised process.
    """
    def bind_existing(self, excel_handle, workbook_handle,
                      policy: SessionPolicy) -> OfflineAdapter: ...


def _project(report, cycle):
    if type(report) is not ObservationalReport:
        raise ValueError('INVALID_REPORT')
    result = to_observational_dict(report)
    if result['cycle_id'] != cycle:
        raise ValueError('OTHER_CYCLE')
    if result['snapshot']['available'] or len(result['samples']) > 1:
        raise ValueError('SNAPSHOT_FORBIDDEN')
    if any(s['sample_position'] != 'FIRST_SAMPLE' for s in result['samples']):
        raise ValueError('SNAPSHOT_FORBIDDEN')
    if any(s['observed_symbol'] not in (None, 'WINZ26') for s in result['samples']):
        raise ValueError('UNEXPECTED_SYMBOL')
    return result


def _factory_spec(factory):
    """Only importable functions and primitive partial arguments; no pickle hooks.

    Reject arbitrary callable instances without inspecting or serializing them.
    This is deliberately narrower than multiprocessing's pickle interface.
    """
    args, kwargs = (), {}
    if type(factory) is functools.partial:
        args, kwargs, factory = factory.args, factory.keywords, factory.func
    if type(factory) is not types.FunctionType:
        raise ValueError('INVALID_FACTORY')
    module, name = factory.__module__, factory.__qualname__
    if (type(module) is not str or type(name) is not str
            or len(module) > 512 or len(name) > 512 or '<' in name):
        raise ValueError('INVALID_FACTORY')
    if module == '__main__':
        path = getattr(sys.modules.get('__main__'), '__file__', None)
        if type(path) is not str or not os.path.isfile(path):
            raise ValueError('INVALID_FACTORY')
        module = os.path.splitext(os.path.basename(path))[0]
    remaining = [256, 8192]
    def primitive(value, depth=0):
        remaining[0] -= 1
        if remaining[0] < 0 or depth > 8:
            raise ValueError('INVALID_FACTORY')
        if type(value) is str:
            remaining[1] -= len(value)
            if remaining[1] < 0:
                raise ValueError('INVALID_FACTORY')
            return value
        if type(value) is int and not -(1 << 63) <= value < (1 << 63):
            raise ValueError('INVALID_FACTORY')
        if type(value) in (int, float, bool, type(None)):
            return value
        if type(value) in (list, tuple) and len(value) <= 64:
            return [primitive(v, depth + 1) for v in value]
        if type(value) is dict and len(value) <= 64 and all(type(k) is str for k in value):
            return {primitive(k, depth + 1): primitive(v, depth + 1) for k, v in value.items()}
        raise ValueError('INVALID_FACTORY')
    spec = [module, name, primitive(args), primitive(kwargs)]
    if len(json.dumps(spec, allow_nan=False)) > 8192:
        raise ValueError('INVALID_FACTORY')
    return spec


# -I -S skips site and main-module replay. Streams are discarded before any
# project/factory import. Only the private duplicated descriptor carries JSON.
_BOOTSTRAP = """
import os, sys
protocol = os.fdopen(os.dup(1), 'wb', buffering=0)
with open(os.devnull, 'w') as sink:
    os.dup2(sink.fileno(), 1)
    os.dup2(sink.fileno(), 2)
import json
sys.path[:] = json.loads(sys.argv[1])
from tools.h10_rc3_18_3_3x2_observational_session import _worker
_worker(protocol, json.loads(sys.argv[2]), json.loads(sys.argv[3]))
"""


def _worker(protocol, spec, policy_values):
    adapter = None
    try:
        policy = SessionPolicy(**policy_values)
        module, name, args, kwargs = spec
        factory = importlib.import_module(module)
        for part in name.split('.'):
            factory = getattr(factory, part)
        adapter = factory(policy, *args, **kwargs)
        previous = None
        for line in sys.stdin.buffer:
            cycle = json.loads(line)
            if cycle is None:
                break
            # A completion anchor conservatively bounds actual starts even
            # when adapter method lookup/dispatch is delayed. Applies to failures.
            if previous is not None:
                while time.monotonic() < previous + policy.interval:
                    time.sleep(max(0, min(.02, previous + policy.interval - time.monotonic())))
            try:
                data = _project(adapter.collect_once(cycle), cycle)
                payload = {'status': 'OBSERVED', 'report': data}
            except BaseException:
                payload = {'status': 'ACQUISITION_OR_REPORT_FAILED', 'report': None}
            finally:
                previous = time.monotonic()
            protocol.write(json.dumps(payload, allow_nan=False).encode('ascii') + b'\n')
    except BaseException:
        pass
    finally:
        if adapter is not None:
            try:
                adapter.close()
            except BaseException:
                pass
        try:
            protocol.close()
        except BaseException:
            pass


def _read_protocol(stream, inbox):
    """Bounded message/queue; never capture stdout/stderr or accumulate output."""
    try:
        while True:
            data = stream.readline(16385)
            if not data or len(data) > 16384 or not data.endswith(b'\n'):
                break
            inbox.put(data)
    except BaseException:
        pass
    finally:
        # One outstanding cycle, hence at most one result and one EOF marker.
        try:
            inbox.put_nowait(None)
        except queue.Full:
            pass


def _quiet_call(owner, name, *args):
    try:
        return getattr(owner, name)(*args)
    except BaseException:
        return None


class ObservationalSession:
    """Explicit offline invocation, one worker per session; no disk output.

    Timeout is terminal: a killed adapter is never retried or reconnected.
    Reports are copied on access. A session object cannot be reused.
    Shutdown time is reserved within the session duration (up to 0.6 seconds).
    Like all user-space deadlines, enforcement depends on OS scheduling.
    """
    def __init__(self, synthetic_factory, policy=None):
        self.policy = policy or SessionPolicy()
        if type(self.policy) is not SessionPolicy:
            raise ValueError('INVALID_POLICY')
        self.policy.__post_init__()
        self._factory = synthetic_factory
        self._reports = deque(maxlen=self.policy.retention)
        self._used = False
        self.worker_stopped = True
        self.stop_reason = 'NOT_STARTED'

    @property
    def reports(self):
        return json.loads(json.dumps(list(self._reports)))

    def run_offline(self, *, stop_event=None):
        if self._used:
            raise RuntimeError('SESSION_ALREADY_USED')
        self._used = True
        process = None
        reader = None
        start = time.monotonic()
        session_end = start + self.policy.duration
        end = session_end - min(.6, self.policy.duration / 4)
        previous = None
        self.stop_reason = 'ATTEMPT_LIMIT'
        try:
            if stop_event is not None and stop_event.is_set():
                self.stop_reason = 'CANCELLED'
                return self.reports
            spec = _factory_spec(self._factory)
            paths = list(sys.path)
            main_path = getattr(sys.modules.get('__main__'), '__file__', None)
            if type(main_path) is str:
                paths.append(os.path.dirname(os.path.abspath(main_path)))
            # All arguments are bounded primitive values, never arbitrary objects.
            command = [sys.executable, '-I', '-S', '-B', '-c', _BOOTSTRAP,
                       json.dumps(paths), json.dumps(spec, allow_nan=False),
                       json.dumps(vars(self.policy), allow_nan=False)]
            inbox = queue.Queue(maxsize=2)
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, bufsize=0,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.worker_stopped = False
            reader = threading.Thread(target=_read_protocol,
                                      args=(process.stdout, inbox), daemon=True)
            reader.start()
            for cycle in range(1, self.policy.max_attempts + 1):
                while previous is not None and time.monotonic() < min(previous + self.policy.interval, end):
                    if stop_event is not None and stop_event.is_set():
                        break
                    time.sleep(min(.02, max(0, min(previous + self.policy.interval, end) - time.monotonic())))
                if stop_event is not None and stop_event.is_set():
                    self.stop_reason = 'CANCELLED'
                    break
                if time.monotonic() >= end:
                    self.stop_reason = 'DURATION_LIMIT'
                    break
                deadline = min(time.monotonic() + self.policy.cycle_timeout, end)
                process.stdin.write(str(cycle).encode('ascii') + b'\n')
                while True:
                    if stop_event is not None and stop_event.is_set():
                        self.stop_reason = 'CANCELLED'
                        break
                    if time.monotonic() >= deadline:
                        self.stop_reason = 'DURATION_LIMIT' if deadline == end else 'CYCLE_TIMEOUT'
                        break
                    try:
                        data = inbox.get(timeout=min(.02, max(0, deadline - time.monotonic())))
                        if data is None:
                            raise ValueError('WORKER_STOPPED')
                        payload = json.loads(data)
                        break
                    except queue.Empty:
                        continue
                if self.stop_reason != 'ATTEMPT_LIMIT':
                    self._reports.append({'cycle_id': cycle, 'status': self.stop_reason, 'report': None})
                    break
                self._reports.append({'cycle_id': cycle, **payload})
                previous = time.monotonic()
        except BaseException:
            self.stop_reason = 'SUPERVISOR_STOPPED'
        finally:
            if process is not None:
                # Every operation is isolated: a failing wait/terminate/close
                # cannot skip the remaining escalation or replace the result.
                _quiet_call(process.stdin, 'write', b'null\n')
                _quiet_call(process.stdin, 'close')
                _quiet_call(process, 'wait', min(.2, max(0, session_end - time.monotonic()) / 3))
                if _quiet_call(process, 'poll') is None:
                    _quiet_call(process, 'terminate')
                    _quiet_call(process, 'wait', min(.2, max(0, session_end - time.monotonic()) / 2))
                if _quiet_call(process, 'poll') is None:
                    _quiet_call(process, 'kill')
                    _quiet_call(process, 'wait', min(.2, max(0, session_end - time.monotonic())))
                self.worker_stopped = _quiet_call(process, 'poll') is not None
                _quiet_call(process.stdout, 'close')
            if reader is not None:
                _quiet_call(reader, 'join', max(0, min(.05, session_end - time.monotonic())))
        return self.reports
