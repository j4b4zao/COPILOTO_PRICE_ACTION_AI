"""Offline prefix continuity over untrusted recovery histories, not persistence."""
from dataclasses import dataclass
from a6_vendor.tools.f3_int44_witness_membership_simulator import Membership
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int51_recovery_memory_simulator import RecoveryMemory, assess_round


@dataclass(frozen=True)
class ContinuityState:
    memory: RecoveryMemory = RecoveryMemory()
    history: tuple = ()
    votes: tuple = ()


@dataclass(frozen=True)
class ContinuityResult(ConcurrentResult):
    state: ContinuityState = ContinuityState()


def assess_continuity(state, round_id, *, max_records=256, **recovery):
    """Accept only extension of the exact caller-held membership/vote prefix.

    Caller replacement of the entire state is undetectable. No storage, signing,
    external pin service, live witnesses or operational authorization exists.
    """
    def reject(status):
        return ContinuityResult(status, state=state)

    if type(max_records) is not int or not 1 <= max_records <= 4096:
        return reject('INVALID_MEMORY_BOUND')
    if (not isinstance(state, ContinuityState) or not isinstance(state.memory, RecoveryMemory)
            or type(state.history) is not tuple or type(state.votes) is not tuple
            or any(not isinstance(m, Membership) for m in state.history)):
        return reject('INVALID_CONTINUITY_STATE')
    if len(state.history) > max_records or len(state.votes) > max_records:
        return reject('CONTINUITY_LIMIT_EXCEEDED')
    if (not state.history and (state.memory != RecoveryMemory() or state.votes)) or (
            state.history and (state.history[-1].epoch != state.memory.epoch
                               or len(state.votes) != len(state.history)-1)):
        return reject('INCONSISTENT_CONTINUITY_STATE')
    history, votes = recovery.get('history'), recovery.get('votes')
    # Tuples are required so snapshots cannot be consumed twice or change in place.
    if type(history) is not tuple or type(votes) is not tuple:
        return reject('INVALID_SNAPSHOT')
    if len(history) > max_records or len(votes) > max_records:
        return reject('CONTINUITY_LIMIT_EXCEEDED')
    if any(not isinstance(m, Membership) for m in history):
        return reject('INVALID_SNAPSHOT')
    if len(history) < len(state.history):
        return reject('TRUNCATED_PREFIX')
    if history[:len(state.history)] != state.history:
        return reject('REWRITTEN_MEMBERSHIP_PREFIX')
    if len(votes) < len(state.votes):
        return reject('TRUNCATED_VOTE_PREFIX')
    if votes[:len(state.votes)] != state.votes:
        return reject('REWRITTEN_VOTE_PREFIX')
    base = assess_round(state.memory, round_id, max_records=max_records, **recovery)
    if base.status != 'RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED':
        return reject(base.status)
    updated = ContinuityState(base.memory, history, votes)
    return ContinuityResult('CONTINUITY_FIXTURE_UNAUTHENTICATED', base.checked, state=updated)


def safe_to_promote(*_args, **_kwargs):
    return False
