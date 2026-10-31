"""Bounded import schedules under one immutable caller-supplied envelope policy."""
from dataclasses import dataclass
from itertools import islice
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int54_schedule_divergence_simulator import schedules
from a6_vendor.tools.f3_int83_concurrent_import_simulator import valid_requests
from a6_vendor.tools.f3_int86_policy_bound_import import valid_policy_snapshot,prepare_policy_import,commit_policy_import


@dataclass(frozen=True)
class PolicyImportRun:
    schedule: tuple
    statuses: tuple
    snapshots: tuple


@dataclass(frozen=True)
class PolicyExploration(ConcurrentResult):
    runs: tuple = ()
    complete: bool = False
    content_divergence: bool = False
    order_divergence: bool = False
    version_divergence: bool = False


def valid_policy_program(initial,batches):
    return (valid_policy_snapshot(initial) and type(batches) is tuple and 1<=len(batches)<=3
            and all(valid_requests(b) for b in batches)
            and sum(len(r.record.blob) for b in batches for r in b)<=33554432)


def run_policy_schedule(initial,batches,schedule):
    if not valid_policy_program(initial,batches) or type(schedule) is not tuple or len(schedule)!=2*len(batches):
        raise ValueError('INVALID_POLICY_SCHEDULE_FIXTURE')
    positions=[0]*len(batches)
    for e in schedule:
        if (type(e) is not tuple or len(e)!=2 or type(e[0]) is not str or type(e[1]) is not int
                or not 0<=e[1]<len(batches) or positions[e[1]]>=2
                or e[0]!=('prepare','commit')[positions[e[1]]]):
            raise ValueError('INVALID_POLICY_SCHEDULE_ORDER')
        positions[e[1]]+=1
    current=initial; proposals={}; statuses=[]; snapshots=[initial]
    for operation,actor in schedule:
        if operation=='prepare':
            result=prepare_policy_import(current,batches[actor]); proposals[actor]=result.proposal
        else:
            result=commit_policy_import(current,proposals[actor]); current=result.snapshot
        statuses.append(result.status); snapshots.append(current)
    return PolicyImportRun(schedule,tuple(statuses),tuple(snapshots))


def explore_policy_imports(initial,batches,*,max_schedules=90):
    if type(max_schedules) is not int or not 1<=max_schedules<=90: return PolicyExploration('INVALID_POLICY_EXPLORATION_BOUND')
    if not valid_policy_program(initial,batches): return PolicyExploration('INVALID_POLICY_EXPLORATION_FIXTURE')
    selected=tuple(islice(schedules(len(batches)),max_schedules+1)); complete=len(selected)<=max_schedules
    runs=tuple(run_policy_schedule(initial,batches,s) for s in selected[:max_schedules]); first=runs[0].snapshots[-1]
    return PolicyExploration('POLICY_SCHEDULES_FIXTURE_UNAUTHENTICATED' if complete else 'POLICY_EXPLORATION_LIMIT_REACHED',
                              len(runs),runs=runs,complete=complete,
                              content_divergence=any(set(r.snapshots[-1].registry.digests)!=set(first.registry.digests) for r in runs),
                              order_divergence=any(r.snapshots[-1].registry.digests!=first.registry.digests for r in runs),
                              version_divergence=any(r.snapshots[-1].version!=first.version for r in runs))


def safe_to_promote(*args,**kwargs): return False
