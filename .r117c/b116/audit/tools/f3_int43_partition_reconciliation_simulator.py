"""F3-INT-43: deterministic OFFLINE partition/witness reconciliation fixtures.

Witness statements are caller-supplied, NOT signed or authenticated. Agreement is
not consensus; no result confers real authority, native certification or closure.
"""
from dataclasses import dataclass
from tools.f3_int41_worker_handoff_simulator import assess_transfers

@dataclass(frozen=True)
class Witness:
    identity: str
    sequence: int
    event: object
    independent: bool = False  # simulated declaration, never verified

@dataclass(frozen=True)
class PartitionResult:
    status: str
    common_events: int = 0
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False
    witness_verified: bool = False


def reconcile_partition(left, right, witnesses=()):
    try:
        left, right, witnesses = tuple(left), tuple(right), tuple(witnesses)
    except TypeError:
        return PartitionResult('INVALID_INPUT')
    if not assess_transfers(left).fixture_consistent or not assess_transfers(right).fixture_consistent:
        return PartitionResult('INVALID_LOCAL_HISTORY')
    common = 0
    for a, b in zip(left, right):
        if a != b:
            break
        common += 1
    if not witnesses:
        return PartitionResult('NO_WITNESS', common)
    if any(not isinstance(w, Witness) or not isinstance(w.identity, str) or not w.identity
           or type(w.sequence) is not int or w.sequence < 1 or type(w.independent) is not bool
           for w in witnesses):
        return PartitionResult('INVALID_WITNESS', common)
    if len({w.identity for w in witnesses}) != len(witnesses):
        return PartitionResult('DUPLICATE_WITNESS_IDENTITY', common)
    if not all(w.independent for w in witnesses):
        return PartitionResult('INDEPENDENCE_NOT_ASSERTED', common)
    # These declarations are NOT proof of actual independence or authentication.
    if any(w.sequence > len(left) or w.sequence > len(right) for w in witnesses):
        return PartitionResult('WITNESS_EVENT_UNAVAILABLE', common)
    if any(left[w.sequence - 1] != w.event or right[w.sequence - 1] != w.event for w in witnesses):
        return PartitionResult('WITNESS_CONFLICT', common)
    if left != right:
        if common == min(len(left), len(right)):
            return PartitionResult('PREFIX_UNCERTAIN', common)
        return PartitionResult('PARTITION_FORK_CONTESTED', common)
    return PartitionResult('AGREED_FIXTURE_UNAUTHENTICATED', common)


def safe_to_promote(*_args, **_kwargs):
    return False
