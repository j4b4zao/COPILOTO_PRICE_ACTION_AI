"""Necessary-condition monitor independent of recovery assessment, offline only.

Passing this monitor does not prove validity: full replay and input assessment
are still required. Invariant-preserving forged traces may pass this monitor.
"""
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int51_recovery_memory_simulator import RecoveryMemory
from tools.f3_int53_interleaving_simulator import valid_snapshot
from tools.f3_int56_bounded_ingestion_simulator import scan, InputRejected


def structural_snapshot(snapshot):
    if not valid_snapshot(snapshot): return False
    state=snapshot.state
    if type(state.memory) is not RecoveryMemory or type(state.history) is not tuple or type(state.votes) is not tuple:
        return False
    memory=state.memory
    return (type(memory.epoch) is int and memory.epoch>=0 and type(memory.digest) is str
            and type(memory.rounds) is tuple and all(type(r) is str and r for r in memory.rounds)
            and len(set(memory.rounds))==len(memory.rounds) and type(memory.consumed) is tuple)


def prefix(before,after):
    return len(after)>=len(before) and after[:len(before)]==before


def assess_transition(before,after,status,*,operation='commit'):
    try:
        scan((before,after,status,operation))
    except InputRejected as error:
        return ConcurrentResult(str(error))
    if (not structural_snapshot(before) or not structural_snapshot(after)
            or type(status) is not str or not status or operation not in ('prepare','commit')):
        return ConcurrentResult('INVALID_MONITOR_FIXTURE')
    if status!='COMMIT_FIXTURE_UNAUTHENTICATED':
        return ConcurrentResult('UNCHANGED_TRANSITION_FIXTURE_UNAUTHENTICATED' if before==after
                                else 'REJECTION_OR_PREPARE_MUTATED_SNAPSHOT')
    if operation!='commit': return ConcurrentResult('COMMIT_STATUS_ON_PREPARE')
    if after.version!=before.version+1: return ConcurrentResult('VERSION_INCREMENT_VIOLATION')
    a,b=before.state,after.state
    if not prefix(a.history,b.history) or not prefix(a.votes,b.votes):
        return ConcurrentResult('CONTINUITY_PREFIX_VIOLATION')
    if b.memory.epoch<a.memory.epoch: return ConcurrentResult('MEMORY_EPOCH_ROLLBACK')
    if (not prefix(a.memory.rounds,b.memory.rounds) or len(b.memory.rounds)!=len(a.memory.rounds)+1):
        return ConcurrentResult('ROUND_APPEND_VIOLATION')
    if (not prefix(a.memory.consumed,b.memory.consumed) or len(b.memory.consumed)<=len(a.memory.consumed)):
        return ConcurrentResult('EVIDENCE_APPEND_VIOLATION')
    if a.memory.epoch==b.memory.epoch and a.memory.digest!=b.memory.digest:
        return ConcurrentResult('SAME_EPOCH_PIN_MUTATION')
    return ConcurrentResult('NECESSARY_COMMIT_INVARIANTS_FIXTURE_UNAUTHENTICATED',1)


def safe_to_promote(*args,**kwargs):
    return False
