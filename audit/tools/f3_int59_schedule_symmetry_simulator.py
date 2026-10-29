"""Independent earliest-commit oracle for symmetric single-snapshot fixtures.

Restricted to identical recovery arguments, unique round IDs and an empty shared
snapshot. Only this finite family is checked; no scheduling fairness is implied.
"""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import Request, valid_requests
from tools.f3_int56_bounded_ingestion_simulator import scan, InputRejected, bounded_prepare
from tools.f3_int58_bounded_exploration_simulator import bounded_explore


@dataclass(frozen=True)
class SymmetryResult(ConcurrentResult):
    complete: bool = False
    winner_counts: tuple = ()


def assess_symmetry(requests, *, max_schedules=4096):
    if (type(requests) is not tuple or not 1<=len(requests)<=4
            or any(type(r) is not Request for r in requests)):
        return SymmetryResult('INVALID_SYMMETRY_FIXTURE')
    try:
        scan(tuple((r.round_id,r.arguments) for r in requests))
    except InputRejected:
        return SymmetryResult('INVALID_SYMMETRY_FIXTURE')
    if (not valid_requests(requests) or len({r.round_id for r in requests})!=len(requests)
            or any(r.arguments!=requests[0].arguments for r in requests)):
        return SymmetryResult('INVALID_SYMMETRY_FIXTURE')
    first=bounded_prepare(Snapshot(),requests[0].round_id,**dict(requests[0].arguments))
    if first.proposal is None:
        return SymmetryResult('INVALID_SYMMETRY_FIXTURE')
    explored=bounded_explore(Snapshot(),requests,max_schedules=max_schedules)
    if not explored.runs:
        return SymmetryResult(explored.status)
    counts={r.round_id:0 for r in requests}
    for run in explored.runs:
        # This oracle uses the schedule alone, not the simulator's status labels.
        expected=requests[next(actor for op,actor in run.schedule if op=='commit')].round_id
        terminal=run.snapshots[-1]
        if terminal.version!=1 or terminal.state.memory.rounds!=(expected,):
            return SymmetryResult('EARLIEST_COMMIT_ORACLE_MISMATCH',explored.checked)
        counts[expected]+=1
    return SymmetryResult('SYMMETRY_FIXTURE_UNAUTHENTICATED' if explored.complete
                          else 'SYMMETRY_EXPLORATION_INCOMPLETE',explored.checked,
                          complete=explored.complete,winner_counts=tuple(counts.items()))


def safe_to_promote(*args, **kwargs):
    return False
