"""Compare necessary transition checks with full finite replay, offline only."""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int54_schedule_divergence_simulator import Run
from tools.f3_int55_divergence_witness_simulator import Witness
from tools.f3_int56_bounded_ingestion_simulator import scan, InputRejected
from tools.f3_int58_bounded_exploration_simulator import bounded_replay
from tools.f3_int64_transition_monitor_simulator import assess_transition


@dataclass(frozen=True)
class DifferentialResult(ConcurrentResult):
    replay_status: str = ''
    violations: tuple = ()


def assess_witness(witness):
    if type(witness) is not Witness or any(type(t) is not Run for t in (witness.left,witness.right)):
        return DifferentialResult('INVALID_DIFFERENTIAL_FIXTURE')
    for trace in (witness.left,witness.right):
        if (type(trace.schedule) is not tuple or not 2<=len(trace.schedule)<=8
                or type(trace.statuses) is not tuple or type(trace.snapshots) is not tuple
                or len(trace.statuses)!=len(trace.schedule) or len(trace.snapshots)!=len(trace.schedule)+1):
            return DifferentialResult('INVALID_DIFFERENTIAL_TRACE')
    try:
        scan(tuple((t.schedule,t.statuses,t.snapshots) for t in (witness.left,witness.right)))
    except InputRejected as error:
        return DifferentialResult(str(error))
    replayed=bounded_replay(witness)
    violations=[]; checked=0
    for side,trace in enumerate((witness.left,witness.right)):
        for i,action in enumerate(trace.schedule):
            if type(action) is not tuple or len(action)!=2 or action[0] not in ('prepare','commit'):
                return DifferentialResult('INVALID_DIFFERENTIAL_TRACE',replay_status=replayed.status)
            verdict=assess_transition(trace.snapshots[i],trace.snapshots[i+1],trace.statuses[i],operation=action[0])
            checked+=1
            if verdict.status not in ('NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED',
                                      'UNCHANGED_TRANSITION_FIXTURE_UNAUTHENTICATED'):
                violations.append((side,i,verdict.status))
    if violations:
        status='TRANSITION_MONITOR_VIOLATION_FIXTURE'
    elif replayed.status!='DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED':
        status='NECESSARY_INVARIANTS_INSUFFICIENT_FIXTURE'
    else:
        status='REPLAY_AND_NECESSARY_INVARIANTS_FIXTURE_UNAUTHENTICATED'
    return DifferentialResult(status,checked,replay_status=replayed.status,violations=tuple(violations))


def safe_to_promote(*args,**kwargs):
    return False
