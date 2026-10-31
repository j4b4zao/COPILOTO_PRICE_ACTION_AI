"""Pinned Windows process identity and Job completion notifications.

Imported by the test supervisor. Job membership authorizes tracking, never a
bare PID. A signaled retained HANDLE, not ActiveProcesses=0, confirms exit.
"""
import ctypes
from ctypes import wintypes as W
import math
import os
import threading
import time

K=ctypes.WinDLL('kernel32',use_last_error=True)
SIGNALLED=0
WAIT_TIMEOUT=258
INVALID_HANDLE=ctypes.c_void_p(-1).value


def check(value):
    if not value:raise ctypes.WinError(ctypes.get_last_error())
    return value


class ProcessEntry(ctypes.Structure):
    _fields_=[('dwSize',W.DWORD),('cntUsage',W.DWORD),('th32ProcessID',W.DWORD),
        ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',W.DWORD),('cntThreads',W.DWORD),
        ('th32ParentProcessID',W.DWORD),('pcPriClassBase',W.LONG),('dwFlags',W.DWORD),('szExeFile',W.WCHAR*260)]


class AssociatePort(ctypes.Structure):
    _fields_=[('CompletionKey',ctypes.c_void_p),('CompletionPort',W.HANDLE)]


K.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]
K.SetInformationJobObject.restype=W.BOOL
K.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4
K.GetProcessTimes.restype=W.BOOL
K.GetProcessId.argtypes=[W.HANDLE];K.GetProcessId.restype=W.DWORD
K.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,ctypes.POINTER(W.BOOL)]
K.IsProcessInJob.restype=W.BOOL
K.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];K.OpenProcess.restype=W.HANDLE
K.CloseHandle.argtypes=[W.HANDLE];K.CloseHandle.restype=W.BOOL
K.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];K.WaitForSingleObject.restype=W.DWORD
K.CreateIoCompletionPort.argtypes=[W.HANDLE,W.HANDLE,ctypes.c_size_t,W.DWORD]
K.CreateIoCompletionPort.restype=W.HANDLE
K.GetQueuedCompletionStatus.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD),ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_void_p),W.DWORD]
K.GetQueuedCompletionStatus.restype=W.BOOL
K.PostQueuedCompletionStatus.argtypes=[W.HANDLE,W.DWORD,ctypes.c_size_t,ctypes.c_void_p]
K.PostQueuedCompletionStatus.restype=W.BOOL
K.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];K.CreateToolhelp32Snapshot.restype=W.HANDLE
K.Process32FirstW.argtypes=[W.HANDLE,ctypes.POINTER(ProcessEntry)];K.Process32FirstW.restype=W.BOOL
K.Process32NextW.argtypes=[W.HANDLE,ctypes.POINTER(ProcessEntry)];K.Process32NextW.restype=W.BOOL


def parent_pid(pid):
    """Diagnostic snapshot only; never proof of process identity or ownership."""
    h=K.CreateToolhelp32Snapshot(2,0)
    if h==INVALID_HANDLE:return None
    try:
        e=ProcessEntry();e.dwSize=ctypes.sizeof(e)
        ok=K.Process32FirstW(h,ctypes.byref(e))
        while ok:
            if e.th32ProcessID==pid:return e.th32ParentProcessID
            ok=K.Process32NextW(h,ctypes.byref(e))
        return None
    finally:K.CloseHandle(h)


def identity_matches(expected,observed):
    return (expected is not None and observed is not None and
            expected['pid']==observed['pid'] and
            expected['creation_100ns']==observed['creation_100ns'])


class ProcessRef:
    def __init__(self,pid,job=None):
        self.handle=check(K.OpenProcess(0x100000|0x1000,False,pid))
        try:
            if job is not None:
                inside=W.BOOL()
                check(K.IsProcessInJob(self.handle,job,ctypes.byref(inside)))
                if not inside.value:raise ValueError('PID is not a member of this Job')
            times=[W.FILETIME() for _ in range(4)]
            check(K.GetProcessTimes(self.handle,*[ctypes.byref(t) for t in times]))
            self.identity=dict(pid=check(K.GetProcessId(self.handle)),ppid=parent_pid(pid),
                creation_100ns=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
        except BaseException:
            K.CloseHandle(self.handle);self.handle=None;raise

    def signalled(self):
        result=K.WaitForSingleObject(self.handle,0)
        if result not in (SIGNALLED,WAIT_TIMEOUT):raise ctypes.WinError(ctypes.get_last_error())
        return result==SIGNALLED

    def wait_until(self,deadline):
        ms=min(0xfffffffe,max(0,math.ceil((deadline-time.monotonic())*1000)))
        result=K.WaitForSingleObject(self.handle,ms)
        if result==WAIT_TIMEOUT:raise TimeoutError('Pinned process termination not signalled: '+repr(self.identity))
        if result!=SIGNALLED:raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            check(K.CloseHandle(self.handle));self.handle=None


class JobTracker:
    """One completion-port consumer retains identities before asynchronous kill.

    An already vanished process can only be confirmed by its EXIT notification
    from this specific Job. Access denied/identity divergence is never treated
    as success; unmatched NEW notifications make cleanup fail closed.
    """
    STOP=0x115001
    BARRIER=0x115002
    KEY=0x115
    def __init__(self,job):
        self.job=job
        self.port=check(K.CreateIoCompletionPort(W.HANDLE(INVALID_HANDLE),None,0,1))
        self.condition=threading.Condition()
        self.records=[]
        self.events=[]
        self.error=None
        self.zero=False
        self.barrier=0
        self.assigned=False
        self.closed=False
        try:
            info=AssociatePort(self.KEY,self.port)
            check(K.SetInformationJobObject(job,7,ctypes.byref(info),ctypes.sizeof(info)))
            self.thread=threading.Thread(target=self._consume,name='115-job-identities')
            self.thread.start()
        except BaseException:
            K.CloseHandle(self.port);raise

    def _consume(self):
        try:
            while True:
                msg=W.DWORD();key=ctypes.c_size_t();pid=ctypes.c_void_p()
                ok=K.GetQueuedCompletionStatus(self.port,ctypes.byref(msg),ctypes.byref(key),ctypes.byref(pid),100)
                if not ok:
                    if ctypes.get_last_error()==WAIT_TIMEOUT:continue
                    raise ctypes.WinError(ctypes.get_last_error())
                if msg.value==self.STOP:return
                with self.condition:
                    if msg.value==self.BARRIER:
                        self.barrier+=1;self.condition.notify_all();continue
                    if key.value!=self.KEY:raise RuntimeError('Unexpected Job notification key')
                    number=int(pid.value or 0)
                    self.events.append(dict(message=msg.value,pid=number,monotonic_ns=time.perf_counter_ns()))
                    if msg.value==6:  # NEW_PROCESS
                        row=dict(pid=number,ref=None,open_error=None,exit_seen=False)
                        try:row['ref']=ProcessRef(number,self.job)
                        except OSError as error:
                            if getattr(error,'winerror',None)!=87:raise
                            row['open_error']=repr(error)
                        self.records.append(row)
                    elif msg.value in (7,8):
                        pending=[r for r in self.records if r['pid']==number and not r['exit_seen']]
                        if not pending:raise RuntimeError('Unmatched Job EXIT notification')
                        pending[0]['exit_seen']=True
                    elif msg.value==4:self.zero=True
                    self.condition.notify_all()
        except BaseException as error:
            with self.condition:
                self.error=repr(error);self.condition.notify_all()

    def _wait(self,predicate,deadline):
        with self.condition:
            while not predicate():
                if self.error:raise RuntimeError('Job tracking failed: '+self.error)
                left=deadline-time.monotonic()
                if left<=0:raise TimeoutError('Job event/identity deadline expired')
                self.condition.wait(left)
            if self.error:raise RuntimeError('Job tracking failed: '+self.error)

    def confirm(self,deadline):
        if self.assigned:
            self._wait(lambda:self.zero,deadline)
        with self.condition:barrier=self.barrier+1
        check(K.PostQueuedCompletionStatus(self.port,self.BARRIER,0,None))
        self._wait(lambda:self.barrier>=barrier,deadline)
        results=[]
        with self.condition:records=list(self.records)
        for row in records:
            ref=row['ref']
            if ref is None:
                self._wait(lambda r=row:r['exit_seen'],deadline)
                results.append(dict(pid=row['pid'],identity=None,proof='OWN_JOB_EXIT_NOTIFICATION',
                                    exit_confirmed=True,open_error=row['open_error']))
            else:
                before=ref.signalled()
                started=time.perf_counter_ns()
                ref.wait_until(deadline)
                results.append(dict(identity=ref.identity,proof='PINNED_HANDLE_SIGNALLED',
                    signalled_before_wait=before,exit_confirmed=ref.signalled(),
                    confirmation_ns=time.perf_counter_ns()-started))
        if self.assigned and not records:raise RuntimeError('No owned processes recorded')
        return results

    def release(self,deadline):
        if self.closed:return
        check(K.PostQueuedCompletionStatus(self.port,self.STOP,0,None))
        self.thread.join(max(0,deadline-time.monotonic()))
        if self.thread.is_alive():raise TimeoutError('Job tracker did not terminate')
        for row in self.records:
            if row['ref']:row['ref'].close()
        check(K.CloseHandle(self.port));self.closed=True
