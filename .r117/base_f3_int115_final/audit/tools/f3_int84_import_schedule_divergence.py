"""Bounded schedule divergence of offline atomic imports, including order vs set."""
from dataclasses import dataclass
from itertools import islice
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int54_schedule_divergence_simulator import schedules
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot,valid_snapshot,valid_requests,prepare_import,commit_import


@dataclass(frozen=True)
class ImportRun:
    schedule: tuple
    statuses: tuple
    snapshots: tuple


@dataclass(frozen=True)
class ImportExploration(ConcurrentResult):
    runs: tuple = ()
    complete: bool = False
    ordered_divergence: bool = False
    content_divergence: bool = False


def run_import_schedule(initial,batches,schedule):
    if (not valid_snapshot(initial) or type(batches) is not tuple or not 1<=len(batches)<=3
            or any(not valid_requests(batch) for batch in batches) or type(schedule) is not tuple or len(schedule)!=2*len(batches)):
        raise ValueError('INVALID_IMPORT_SCHEDULE_FIXTURE')
    prepared=set(); committed=set(); proposals={}; current=initial; statuses=[]; snapshots=[initial]
    for event in schedule:
        if (type(event) is not tuple or len(event)!=2 or type(event[1]) is not int or not 0<=event[1]<len(batches)):
            raise ValueError('INVALID_IMPORT_SCHEDULE_EVENT')
        operation,actor=event
        if operation=='prepare' and actor not in prepared:
            result=prepare_import(current,batches[actor]); proposals[actor]=result.proposal; prepared.add(actor)
        elif operation=='commit' and actor in prepared and actor not in committed:
            result=commit_import(current,proposals[actor]); current=result.snapshot; committed.add(actor)
        else: raise ValueError('INVALID_IMPORT_SCHEDULE_ORDER')
        statuses.append(result.status); snapshots.append(current)
    return ImportRun(schedule,tuple(statuses),tuple(snapshots))


def explore_imports(initial,batches,*,max_schedules=90):
    if type(max_schedules) is not int or not 1<=max_schedules<=90:
        return ImportExploration('INVALID_IMPORT_EXPLORATION_BOUND')
    if (not valid_snapshot(initial) or type(batches) is not tuple or not 1<=len(batches)<=3
            or any(not valid_requests(batch) for batch in batches)):
        return ImportExploration('INVALID_IMPORT_EXPLORATION_FIXTURE')
    if sum(len(r.record.blob) for batch in batches for r in batch)>33554432:
        return ImportExploration('IMPORT_EXPLORATION_BYTE_LIMIT')
    selected=tuple(islice(schedules(len(batches)),max_schedules+1)); complete=len(selected)<=max_schedules
    runs=tuple(run_import_schedule(initial,batches,s) for s in selected[:max_schedules])
    first=runs[0].snapshots[-1].registry.digests
    ordered=any(run.snapshots[-1].registry.digests!=first for run in runs[1:])
    content=any(frozenset(run.snapshots[-1].registry.digests)!=frozenset(first) for run in runs[1:])
    return ImportExploration('IMPORT_SCHEDULES_FIXTURE_UNAUTHENTICATED' if complete else 'IMPORT_EXPLORATION_LIMIT_REACHED',
                              len(runs),runs=runs,complete=complete,ordered_divergence=ordered,content_divergence=content)


def safe_to_promote(*args,**kwargs): return False
