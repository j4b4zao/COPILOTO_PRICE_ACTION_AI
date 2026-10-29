"""Bounded offline process/pipe supervision on Windows.

Every child starts at a gate before user code. Assignment to a kill-on-close
Job Object precedes releasing the gate; descendants inherit that job. Failure
to obtain containment is fatal. These are test facilities, not native fencing.
"""
import ctypes
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

MAX_BYTES = 2 * 1024 * 1024
MAX_OUTPUT = 8 * 1024 * 1024
CLEANUP_SECONDS = 5


class OutputLimitError(RuntimeError):
    pass


if os.name == 'nt':
    K = ctypes.WinDLL('kernel32', use_last_error=True)
    class BasicLimits(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64),
                    ('PerJobUserTimeLimit', ctypes.c_int64), ('LimitFlags', W.DWORD),
                    ('MinimumWorkingSetSize', ctypes.c_size_t), ('MaximumWorkingSetSize', ctypes.c_size_t),
                    ('ActiveProcessLimit', W.DWORD), ('Affinity', ctypes.c_size_t),
                    ('PriorityClass', W.DWORD), ('SchedulingClass', W.DWORD)]
    class IOCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ('ReadOperationCount','WriteOperationCount',
                    'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
    class ExtendedLimits(ctypes.Structure):
        _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IOCounters),
                    ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]
    class Accounting(ctypes.Structure):
        _fields_ = [(n, ctypes.c_int64) for n in ('TotalUserTime','TotalKernelTime',
                    'ThisPeriodTotalUserTime','ThisPeriodTotalKernelTime')] + [
                    (n, W.DWORD) for n in ('TotalPageFaultCount','TotalProcesses',
                    'ActiveProcesses','TotalTerminatedProcesses')]
    K.CreateJobObjectW.argtypes = [ctypes.c_void_p, W.LPCWSTR]
    K.CreateJobObjectW.restype = W.HANDLE
    K.SetInformationJobObject.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD]
    K.SetInformationJobObject.restype = W.BOOL
    K.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
    K.AssignProcessToJobObject.restype = W.BOOL
    K.TerminateJobObject.argtypes = [W.HANDLE, W.UINT]
    K.TerminateJobObject.restype = W.BOOL
    K.QueryInformationJobObject.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD, ctypes.c_void_p]
    K.QueryInformationJobObject.restype = W.BOOL
    K.CloseHandle.argtypes = [W.HANDLE]
    K.CloseHandle.restype = W.BOOL
    K.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    K.OpenProcess.restype = W.HANDLE
    K.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    K.WaitForSingleObject.restype = W.DWORD


def wincheck(value):
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())
    return value


class Job:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Windows Job containment required; no permissive fallback')
        self.handle = wincheck(K.CreateJobObjectW(None, None))
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        try:
            wincheck(K.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        except BaseException:
            K.CloseHandle(self.handle)
            raise
        self.lock = threading.Lock()
        from tools.f3_int115_process_identity import JobTracker
        try:
            self.tracker = JobTracker(self.handle)
        except BaseException:
            K.CloseHandle(self.handle)
            raise

    def assign(self, process):
        wincheck(K.AssignProcessToJobObject(self.handle, W.HANDLE(int(process._handle))))
        self.tracker.assigned = True

    def terminate(self):
        with self.lock:
            if self.handle:
                wincheck(K.TerminateJobObject(self.handle, 91))

    def active(self):
        info = Accounting()
        wincheck(K.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None))
        return info.ActiveProcesses

    def close(self, deadline=None):
        self.tracker.release(deadline if deadline is not None else time.monotonic()+CLEANUP_SECONDS)
        with self.lock:
            if self.handle:
                wincheck(K.CloseHandle(self.handle))
                self.handle = None


def process_running(pid):
    handle = K.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
    if not handle:
        if ctypes.get_last_error() == 87:  # invalid PID
            return False
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return K.WaitForSingleObject(handle, 0) == 258
    finally:
        K.CloseHandle(handle)


class Peer:
    def __init__(self, command, *, cwd, timeout=60, output=None):
        if timeout <= 0:
            raise ValueError('Positive deadline required')
        self.deadline = time.monotonic() + timeout
        self.failure = None
        self.events = queue.Queue(maxsize=128)
        self.stderr = bytearray()
        self.readers = []
        self.writers = []
        self.closed = False
        self.cleanup = None
        self.stop = threading.Event()
        self.job = Job()
        self.process = None
        self.assigned = False
        self.watchdog = None
        try:
            gate = [sys.executable, '-B', str(Path(__file__).resolve()), '--gate', json.dumps(command[1:])]
            self.process = subprocess.Popen(gate, cwd=cwd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE if output is None else output,
                stderr=subprocess.PIPE if output is None else subprocess.STDOUT,
                bufsize=0, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            self.job.assign(self.process)
            self.assigned = True
            self.watchdog = threading.Thread(target=self._watch, name='115-deadline')
            self.watchdog.start()
            if output is None:
                for name in ('stdout','stderr'):
                    thread = threading.Thread(target=self._drain, args=(name,), name='115-'+name)
                    self.readers.append(thread)
                    thread.start()
            self._write(b'G')  # No target code executes before job assignment.
        except BaseException:
            self.close()
            raise

    @property
    def pid(self):
        return self.process.pid

    def poll(self):
        return self.process.poll()

    def _watch(self):
        if not self.stop.wait(max(0, self.deadline-time.monotonic())):
            self._fail(TimeoutError('Process/IPC deadline expired'))

    def _fail(self, error):
        if self.failure is None:
            self.failure = error
        self.job.terminate()
        try:
            self.events.put_nowait(None)
        except queue.Full:
            pass

    def remaining(self):
        if self.failure is not None:
            raise self.failure
        remaining = self.deadline-time.monotonic()
        if remaining <= 0:
            self._fail(TimeoutError('Process/IPC deadline expired'))
            raise self.failure
        return remaining

    def _drain(self, name):
        stream = getattr(self.process, name)
        pending = bytearray()
        total = 0
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_OUTPUT:
                    self._fail(OutputLimitError(name+' output limit'))
                    break
                if name == 'stderr':
                    self.stderr.extend(chunk)
                else:
                    pending.extend(chunk)
                    if len(pending) > MAX_BYTES:
                        self._fail(OutputLimitError('stdout line limit'))
                        break
                    while b'\n' in pending:
                        line, _, rest = pending.partition(b'\n')
                        pending = bytearray(rest)
                        try:
                            self.events.put_nowait(bytes(line))
                        except queue.Full:
                            self._fail(OutputLimitError('stdout queue limit'))
                            return
            if name == 'stdout':
                if pending:
                    self._fail(RuntimeError('Truncated stdout frame'))
                try:
                    self.events.put_nowait(None)
                except queue.Full:
                    self._fail(OutputLimitError('stdout queue limit'))
        except BaseException as error:
            self._fail(error)

    def _write(self, data):
        errors = []
        def write():
            try:
                view = memoryview(data)
                while view:
                    count = os.write(self.process.stdin.fileno(), view)
                    if not count:
                        raise BrokenPipeError('Zero-length pipe write')
                    view = view[count:]
            except BaseException as error:
                errors.append(error)
        thread = threading.Thread(target=write, name='115-stdin')
        self.writers.append(thread)
        thread.start()
        thread.join(self.remaining())
        if thread.is_alive():
            self._fail(TimeoutError('stdin write deadline expired'))
        self.remaining()
        if errors:
            raise errors[0]

    def send(self, value):
        data = (value+'\n').encode('utf8')
        if len(data) > MAX_BYTES:
            raise ValueError('Input frame too large')
        try:
            self._write(data)
        except BaseException:
            self.close()
            raise

    def recv(self):
        try:
            line = self.events.get(timeout=self.remaining())
            self.remaining()
            if line is None:
                raise EOFError('Worker ended before the expected frame')
            return json.loads(line.decode('utf8'))
        except queue.Empty:
            self._fail(TimeoutError('stdout read deadline expired'))
            self.close()
            raise self.failure
        except BaseException:
            self.close()
            raise

    def wait(self, timeout=None):
        try:
            return self.process.wait(timeout=min(self.remaining(), timeout) if timeout else self.remaining())
        except subprocess.TimeoutExpired:
            self._fail(TimeoutError('process wait deadline expired'))
            raise self.failure

    def kill(self):
        self.job.terminate()

    def close(self):
        if self.closed:
            if self.cleanup and not self.cleanup['confirmed']:
                raise RuntimeError(self.cleanup['error'])
            return
        started=time.perf_counter_ns()
        until=time.monotonic()+CLEANUP_SECONDS
        confirmed=[]
        error=None
        active=None
        alive=[]
        try:
            self.stop.set()
            if self.watchdog is not None:
                self.watchdog.join(max(0,until-time.monotonic()))
                if self.watchdog.is_alive():raise TimeoutError('Watchdog cleanup deadline')
            self.job.terminate()  # Asynchronous: request alone is not exit proof.
            if self.process is not None:
                if not self.assigned and self.process.poll() is None:
                    self.process.kill()
                self.process.wait(timeout=max(0,until-time.monotonic()))
            confirmed=self.job.tracker.confirm(until)
            active=self.job.active()
            for thread in self.readers+self.writers:
                thread.join(max(0,until-time.monotonic()))
            alive=[t.name for t in self.readers+self.writers if t.is_alive()]
            if active or alive:raise RuntimeError('Incomplete process/IPC cleanup')
        except BaseException as caught:
            error=repr(caught)
        finally:
            try:
                # A finite emergency grace only releases tracker resources;
                # it cannot change a failed cleanup into successful evidence.
                self.job.close(deadline=max(until,time.monotonic()+1))
            except BaseException as caught:
                error=error or repr(caught)
            if self.process is not None and not alive:
                for name in ('stdin','stdout','stderr'):
                    stream=getattr(self.process,name)
                    if stream is not None:stream.close()
            self.cleanup=dict(confirmed=error is None,active_processes=active,
                live_io_threads=alive,direct_exit_code=self.process.returncode if self.process else None,
                processes=confirmed,job_events=list(self.job.tracker.events),
                tracker_error=self.job.tracker.error,error=error,
                elapsed_ns=time.perf_counter_ns()-started)
            self.closed=True
        if error:raise RuntimeError('Cleanup not confirmed: '+error)


def run_supervised(command, *, cwd, log, timeout):
    started = time.monotonic()
    peer = None
    result = dict(command=command, timed_out=False, exception=None, exit_code=None, cleanup=None)
    try:
        with Path(log).open('xb') as output:
            try:
                peer = Peer(command, cwd=cwd, timeout=timeout, output=output)
                result['exit_code'] = peer.wait()
            except TimeoutError as error:
                result.update(timed_out=True, exception=str(error))
            except Exception as error:
                result['exception'] = repr(error)
            finally:
                if peer is not None:
                    try:
                        peer.close()
                    except Exception as error:
                        result['exception'] = result['exception'] or ('CLEANUP_FAILURE: '+repr(error))
                    finally:
                        result['cleanup'] = peer.cleanup
                        result['exit_code'] = peer.process.returncode
    finally:
        result['seconds'] = round(time.monotonic()-started, 3)
        Path(str(log)+'.execution.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    return result


def gate():
    # The parent watchdog enforces the deadline even while this read blocks.
    if os.read(0, 1) != b'G':
        raise RuntimeError('Job gate not released')
    import runpy
    args = json.loads(sys.argv[2])
    while args and args[0] in ('-B','-u'):
        args.pop(0)
    sys.path.insert(0, str(Path.cwd()))
    if args[0] == '-c':
        sys.argv = ['-c']+args[2:]
        exec(compile(args[1], '<supervised>', 'exec'), {'__name__':'__main__'})
    elif args[0] == '-m':
        sys.argv = [args[1]]+args[2:]
        runpy.run_module(args[1], run_name='__main__', alter_sys=True)
    else:
        sys.argv = args
        runpy.run_path(args[0], run_name='__main__')


if __name__ == '__main__':
    gate()
