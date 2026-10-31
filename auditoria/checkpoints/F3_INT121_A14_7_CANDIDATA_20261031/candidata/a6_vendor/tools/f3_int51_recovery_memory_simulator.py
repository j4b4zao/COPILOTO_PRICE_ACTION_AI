"""Immutable caller-controlled recovery memory, offline and unauthenticated.

Memory is not durable, trusted, signed or protected from caller replacement.
Rejecting replay in this fixture does not establish real replay protection.
"""
from dataclasses import dataclass
from itertools import islice
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import (
    ConcurrentResult, assess_concurrent,
)


@dataclass(frozen=True)
class RecoveryMemory:
    epoch: int = 0
    digest: str = ''
    rounds: tuple = ()
    consumed: tuple = ()


@dataclass(frozen=True)
class RoundResult(ConcurrentResult):
    memory: RecoveryMemory = RecoveryMemory()


def assess_round(memory, round_id, *, max_records=256, **recovery):
    def reject(status):
        return RoundResult(status, memory=memory)

    if type(max_records) is not int or not 1 <= max_records <= 4096:
        return reject('INVALID_MEMORY_BOUND')
    if (not isinstance(memory, RecoveryMemory) or type(memory.epoch) is not int
            or memory.epoch < 0 or type(memory.digest) is not str
            or (memory.epoch == 0) != (memory.digest == '')
            or type(memory.rounds) is not tuple or type(memory.consumed) is not tuple):
        return reject('INVALID_MEMORY')
    if len(memory.rounds) > max_records or len(memory.consumed) > max_records:
        return reject('MEMORY_LIMIT_EXCEEDED')
    if (any(type(r) is not str or not r for r in memory.rounds)
            or len(set(memory.rounds)) != len(memory.rounds)
            or any(type(token) is not tuple or len(token) != 3
                   or type(token[0]) is not str or not token[0]
                   or type(token[1]) is not int or not 1 <= token[1] <= memory.epoch
                   or type(token[2]) is not str or not token[2]
                   or (token[1] == memory.epoch and token[2] != memory.digest)
                   for token in memory.consumed)):
        return reject('INVALID_MEMORY')
    if len(set(memory.consumed)) != len(memory.consumed):
        return reject('INVALID_MEMORY')
    if (memory.epoch == 0 and (memory.rounds or memory.consumed)) or (
            memory.epoch > 0 and (not memory.rounds or not memory.consumed)):
        return reject('INVALID_MEMORY')
    if type(round_id) is not str or not round_id:
        return reject('INVALID_ROUND_ID')
    if round_id in memory.rounds:
        return reject('REPLAYED_ROUND')
    required = {'history', 'votes', 'reference', 'returned'}
    allowed = required | {'offline', 'evidence', 'copies', 'pinned_digest', 'partitioned', 'max_steps'}
    if not required.issubset(recovery) or set(recovery) - allowed:
        return reject('INVALID_RECOVERY_ARGUMENTS')
    reference = recovery.get('reference')
    if (type(reference) is not tuple or not reference
            or any(type(e) is not int or e < 1 for e in reference)):
        return reject('INVALID_REFERENCE')
    if reference[-1] < memory.epoch:
        return reject('EPOCH_ROLLBACK')
    if reference[-1] == memory.epoch and recovery.get('pinned_digest') != memory.digest:
        return reject('PIN_CONFLICT_WITH_MEMORY')
    try:
        evidence = tuple(islice(iter(recovery.get('evidence', ())), max_records + 1))
    except (TypeError, ValueError):
        return reject('INVALID_EVIDENCE')
    if len(evidence) > max_records:
        return reject('MEMORY_LIMIT_EXCEEDED')
    recovery['evidence'] = evidence
    base = assess_concurrent(**recovery)
    if base.status != 'CONCURRENT_RECOVERY_FIXTURE_UNAUTHENTICATED':
        return reject(base.status if base.status.startswith('BASE_') else 'BASE_' + base.status)
    tokens = tuple((e.witness, e.epoch, e.digest) for e in evidence)
    if set(tokens).intersection(memory.consumed):
        return reject('REPLAYED_CROSS_ROUND_EVIDENCE')
    if len(memory.rounds) + 1 > max_records or len(memory.consumed) + len(tokens) > max_records:
        return reject('MEMORY_LIMIT_EXCEEDED')
    updated = RecoveryMemory(reference[-1], recovery['pinned_digest'],
                             memory.rounds + (round_id,), memory.consumed + tokens)
    return RoundResult('RECOVERY_MEMORY_FIXTURE_UNAUTHENTICATED', len(tokens), memory=updated)


def safe_to_promote(*_args, **_kwargs):
    return False
