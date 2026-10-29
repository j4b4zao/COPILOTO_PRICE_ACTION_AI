"""Replayable divergence witnesses over caller-supplied offline fixtures.

Witnesses have no signatures, independent provenance or certification. Replaying
two traces confirms only that this finite simulator reproduces their divergence.
"""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int54_schedule_divergence_simulator import (
    Run, explore, run_schedule, valid_requests)
from tools.f3_int53_interleaving_simulator import valid_snapshot


@dataclass(frozen=True)
class Witness:
    initial: object
    requests: tuple
    left: Run
    right: Run


@dataclass(frozen=True)
class WitnessResult(ConcurrentResult):
    witness: object = None
    complete: bool = False


def replay(witness):
    if (type(witness) is not Witness or not valid_snapshot(witness.initial)
            or not valid_requests(witness.requests)
            or type(witness.left) is not Run or type(witness.right) is not Run):
        return WitnessResult('INVALID_WITNESS')
    for trace in (witness.left,witness.right):
        if (type(trace.statuses) is not tuple or type(trace.snapshots) is not tuple
                or len(trace.statuses)!=2*len(witness.requests)
                or len(trace.snapshots)!=len(trace.statuses)+1):
            return WitnessResult('INVALID_TRACE_SHAPE')
        try:
            actual=run_schedule(witness.initial,witness.requests,trace.schedule)
        except (TypeError,ValueError):
            return WitnessResult('INVALID_TRACE_SCHEDULE')
        if actual != trace:
            return WitnessResult('TRACE_REPLAY_MISMATCH')
    if witness.left.snapshots[-1] == witness.right.snapshots[-1]:
        return WitnessResult('NO_TERMINAL_DIVERGENCE')
    return WitnessResult('DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED',2,witness=witness)


def find_witness(initial, requests, *, max_schedules=128):
    result=explore(initial,requests,max_schedules=max_schedules)
    if not result.runs:
        return WitnessResult(result.status)
    first=result.runs[0]
    for trace in result.runs[1:]:
        if first.snapshots[-1]!=trace.snapshots[-1]:
            witness=Witness(initial,requests,first,trace)
            checked=replay(witness)
            return WitnessResult(checked.status,result.checked,witness=checked.witness,
                                 complete=result.complete)
    return WitnessResult('NO_DIVERGENCE_IN_EXPLORED_FIXTURES' if result.complete
                         else 'INCOMPLETE_WITHOUT_WITNESS',result.checked,
                         complete=result.complete)


def safe_to_promote(*args, **kwargs):
    return False
