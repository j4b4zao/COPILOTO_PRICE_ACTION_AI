"""Bounded interleavings of fixed prepare/crash/late-commit/restart programs."""
from dataclasses import dataclass
from itertools import islice
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int57_retry_interleaving_simulator import valid_request
from tools.f3_int66_crash_schedule_simulator import run_crash_schedule

PROGRAM=(('prepare',0),('crash',0),('commit',0),('prepare',1),('commit',1))


@dataclass(frozen=True)
class CrashExploration(ConcurrentResult):
    complete: bool = False
    runs: tuple = ()


def interleavings(count):
    if type(count) is not int or not 1<=count<=3:
        raise ValueError('actor bound')
    def walk(prefix,positions):
        if all(p==len(PROGRAM) for p in positions):
            yield prefix
            return
        for actor,position in enumerate(positions):
            if position<len(PROGRAM):
                op,generation=PROGRAM[position]
                updated=positions[:actor]+(position+1,)+positions[actor+1:]
                yield from walk(prefix+((op,actor,generation),),updated)
    yield from walk((),(0,)*count)


def explore_crashes(requests,*,max_schedules=512):
    if type(max_schedules) is not int or not 1<=max_schedules<=512:
        return CrashExploration('INVALID_CRASH_EXPLORATION_BOUND')
    if (type(requests) is not tuple or not 1<=len(requests)<=3
            or any(not valid_request(r) for r in requests)):
        return CrashExploration('INVALID_CRASH_EXPLORATION_FIXTURE')
    selected=tuple(islice(interleavings(len(requests)),max_schedules+1))
    complete=len(selected)<=max_schedules
    runs=tuple(run_crash_schedule(Snapshot(),requests,events) for events in selected[:max_schedules])
    return CrashExploration('CRASH_INTERLEAVINGS_FIXTURE_UNAUTHENTICATED' if complete
                            else 'CRASH_EXPLORATION_LIMIT_REACHED',len(runs),complete=complete,runs=runs)


def safe_to_promote(*args,**kwargs):
    return False
