"""Bounded actor crash/restart fixture model; no durable storage or native fence."""
from dataclasses import dataclass
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int53_interleaving_simulator import Snapshot, valid_snapshot
from a6_vendor.tools.f3_int54_schedule_divergence_simulator import Request
from a6_vendor.tools.f3_int56_bounded_ingestion_simulator import scan, InputRejected, bounded_prepare, bounded_commit
from a6_vendor.tools.f3_int57_retry_interleaving_simulator import valid_request


@dataclass(frozen=True)
class CrashResult(ConcurrentResult):
    snapshot: Snapshot = Snapshot()
    generations: tuple = ()
    trace: tuple = ()


def run_crash_schedule(initial,requests,events,*,max_events=16):
    def reject(status): return CrashResult(status,snapshot=initial)
    if type(max_events) is not int or not 1<=max_events<=64:
        return reject('INVALID_CRASH_BOUND')
    if (not valid_snapshot(initial) or type(requests) is not tuple or not 1<=len(requests)<=4
            or any(not valid_request(r) for r in requests) or type(events) is not tuple
            or not 1<=len(events)<=max_events):
        return reject('INVALID_CRASH_FIXTURE')
    try:
        scan((initial,events))
    except InputRejected as error:
        return reject(str(error))
    # Validate the entire event shape before any simulated transition.
    if any(type(e) is not tuple or len(e)!=3 or type(e[0]) is not str
           or e[0] not in ('prepare','commit','crash') or type(e[1]) is not int
           or not 0<=e[1]<len(requests) or type(e[2]) is not int or not 0<=e[2]<=64 for e in events):
        return reject('INVALID_CRASH_EVENT')
    current=initial; generations=[0]*len(requests); pending={}; trace=[]
    for op,actor,generation in events:
        if generation!=generations[actor]:
            status='STALE_ACTOR_GENERATION'
        elif op=='crash':
            generations[actor]+=1; pending.pop(actor,None)
            status='ACTOR_CRASH_FIXTURE_UNAUTHENTICATED'
        elif op=='prepare':
            item=requests[actor]
            result=bounded_prepare(current,item.round_id,**dict(item.arguments))
            if result.proposal is None: pending.pop(actor,None)
            else: pending[actor]=result.proposal
            status=result.status
        elif actor not in pending:
            status='NO_PENDING_PROPOSAL'
        else:
            result=bounded_commit(current,pending.pop(actor))
            current=result.snapshot; status=result.status
        trace.append((op,actor,generation,status,current,tuple(generations)))
    return CrashResult('CRASH_SCHEDULE_FIXTURE_UNAUTHENTICATED',len(events),
                       snapshot=current,generations=tuple(generations),trace=tuple(trace))


def safe_to_promote(*args,**kwargs):
    return False
