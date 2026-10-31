"""Replayable finite crash-interleaving divergence witnesses; unauthenticated."""
from dataclasses import dataclass
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int53_interleaving_simulator import Snapshot
from a6_vendor.tools.f3_int56_bounded_ingestion_simulator import scan, InputRejected
from a6_vendor.tools.f3_int57_retry_interleaving_simulator import valid_request
from a6_vendor.tools.f3_int66_crash_schedule_simulator import CrashResult, run_crash_schedule
from a6_vendor.tools.f3_int67_crash_exploration_simulator import explore_crashes


@dataclass(frozen=True)
class CrashWitness:
    requests: tuple
    left: CrashResult
    right: CrashResult


@dataclass(frozen=True)
class CrashWitnessResult(ConcurrentResult):
    witness: object = None
    complete: bool = False


def replay_crash_witness(witness):
    if (type(witness) is not CrashWitness or type(witness.requests) is not tuple
            or not 1<=len(witness.requests)<=3 or any(not valid_request(r) for r in witness.requests)
            or any(type(t) is not CrashResult for t in (witness.left,witness.right))):
        return CrashWitnessResult('INVALID_CRASH_WITNESS')
    for trace in (witness.left,witness.right):
        if type(trace.trace) is not tuple or not 1<=len(trace.trace)<=16:
            return CrashWitnessResult('INVALID_CRASH_WITNESS_TRACE')
        try:
            scan((trace.trace,trace.snapshot,trace.generations))
        except InputRejected as error:
            return CrashWitnessResult(str(error))
        if any(type(row) is not tuple or len(row)!=6 for row in trace.trace):
            return CrashWitnessResult('INVALID_CRASH_WITNESS_TRACE')
        events=tuple(row[:3] for row in trace.trace)
        actual=run_crash_schedule(Snapshot(),witness.requests,events)
        if actual!=trace:
            return CrashWitnessResult('CRASH_TRACE_REPLAY_MISMATCH')
    if witness.left.snapshot==witness.right.snapshot:
        return CrashWitnessResult('NO_CRASH_TERMINAL_DIVERGENCE')
    return CrashWitnessResult('CRASH_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED',2,witness=witness)


def find_crash_witness(requests,*,max_schedules=512):
    explored=explore_crashes(requests,max_schedules=max_schedules)
    if not explored.runs: return CrashWitnessResult(explored.status)
    first=explored.runs[0]
    for trace in explored.runs[1:]:
        if trace.snapshot!=first.snapshot:
            witness=CrashWitness(requests,first,trace)
            result=replay_crash_witness(witness)
            return CrashWitnessResult(result.status,explored.checked,witness=result.witness,complete=explored.complete)
    return CrashWitnessResult('NO_CRASH_DIVERGENCE_IN_EXPLORED_FIXTURES' if explored.complete
                              else 'INCOMPLETE_WITHOUT_CRASH_WITNESS',explored.checked,complete=explored.complete)


def safe_to_promote(*args,**kwargs):
    return False
