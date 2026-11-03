"""Private first-attempt budget guard; no operational API integration.

An injected clock is for deterministic tests. Retry budgets do not bound OS
calls, scheduling or arbitrary observer callbacks.
"""
import time
import f3_int121_a14_8_journal as journal


def read(path,expected,timeout=0.5,after_denial=None,clock_ns=None):
    if type(timeout) not in (int,float) or not 0<timeout<=5:
        raise ValueError('Private retry budget must be positive and at most five seconds')
    clock=clock_ns if clock_ns is not None else time.perf_counter_ns
    started=clock()
    deadline=started+int(timeout*1_000_000_000)
    attempts=[]
    raw=None
    error=None
    verification=None
    status=None
    while True:
        begin=clock()
        if begin>=deadline:
            status='JOURNAL_READ_DENIED' if attempts else 'JOURNAL_READ_BUDGET_EXHAUSTED'
            break
        try:
            raw=path.read_bytes()
        except OSError as caught:
            error=dict(type=type(caught).__name__,errno=caught.errno,
                       winerror=getattr(caught,'winerror',None),message=str(caught))
            attempts.append(dict(started_ns=begin,finished_ns=clock(),error=dict(error)))
            if isinstance(caught,FileNotFoundError):
                status='JOURNAL_MISSING'; break
            if not isinstance(caught,PermissionError):
                status='JOURNAL_READ_ERROR'; break
            if after_denial is not None: after_denial(dict(error))
            remaining=(deadline-clock())/1_000_000_000
            if remaining>0: time.sleep(min(0.01,remaining))
        else:
            attempts.append(dict(started_ns=begin,finished_ns=clock(),error=None))
            verification=journal.compare(raw,expected)
            status=verification['reason']
            error=None
            break
    return dict(status=status,raw=raw,error=error,verification=verification,attempts=attempts,
                started_ns=started,deadline_ns=deadline,finished_ns=clock(),
                first_attempt_budget_checked=True,strict_deadline_guaranteed=False,production_api_changed=False)
