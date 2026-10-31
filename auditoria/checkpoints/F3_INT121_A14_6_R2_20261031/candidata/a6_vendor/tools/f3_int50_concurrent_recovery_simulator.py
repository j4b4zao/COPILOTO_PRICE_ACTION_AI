"""Caller-supplied concurrent recovery fixtures. Offline; never authorization."""
from dataclasses import dataclass
from itertools import islice
from a6_vendor.tools.f3_int49_recovery_replay_simulator import assess_recovery
from a6_vendor.tools.f3_int44_witness_membership_simulator import Membership


@dataclass(frozen=True)
class EpochEvidence:
    witness: str
    epoch: int
    digest: str


@dataclass(frozen=True)
class ConcurrentResult:
    status: str
    checked: int = 0
    f3: str = 'OPEN'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def assess_concurrent(history, votes, *, reference, returned, offline=(),
                      evidence=(), copies=(), pinned_digest=None,
                      partitioned=False, max_steps=64):
    """Require one pinned epoch/digest per returned witness; do not select winners.

    All pins, identities and digests are untrusted fixture metadata. Bounded
    consumption limits each input to max_steps + 1 items, including iterators.
    """
    if type(max_steps) is not int or not 2 <= max_steps <= 4096:
        return ConcurrentResult('INVALID_BOUNDS')
    if type(partitioned) is not bool:
        return ConcurrentResult('INVALID_PARTITION_FLAG')
    inputs = []
    try:
        for value in (history, votes, reference, returned, offline, evidence, copies):
            items = tuple(islice(iter(value), max_steps + 1))
            if len(items) > max_steps:
                return ConcurrentResult('INPUT_LIMIT_EXCEEDED')
            inputs.append(items)
    except (TypeError, ValueError):
        return ConcurrentResult('INVALID_INPUT')
    history, votes, reference, returned, offline, evidence, copies = inputs
    if any(not isinstance(m, Membership) or type(m.epoch) is not int
           or m.epoch < 1 or type(m.predecessor) is not int
           or not 0 <= m.predecessor < m.epoch
           or type(m.members) is not tuple or not m.members
           or len(m.members) > max_steps
           or any(type(w) is not str or not w for w in m.members)
           or len(set(m.members)) != len(m.members)
           or type(m.threshold) is not int or not 1 <= m.threshold <= len(m.members)
           for m in history):
        return ConcurrentResult('INVALID_MEMBERSHIP')
    if any(type(pair) is not tuple or len(pair) != 2
           or any(type(group) is not tuple or len(group) > max_steps
                  or any(type(w) is not str or not w for w in group)
                  for group in pair) for pair in votes):
        return ConcurrentResult('INVALID_VOTES')
    if (not reference or any(type(e) is not int or e < 1 for e in reference)
            or any(a >= b for a, b in zip(reference, reference[1:]))):
        return ConcurrentResult('INVALID_REFERENCE')
    if type(pinned_digest) is not str or not pinned_digest:
        return ConcurrentResult('MISSING_DIGEST_PIN')
    if any(not isinstance(e, EpochEvidence) or type(e.witness) is not str
           or not e.witness or type(e.epoch) is not int or e.epoch < 1
           or type(e.digest) is not str or not e.digest for e in evidence):
        return ConcurrentResult('INVALID_EVIDENCE')
    seen = {}
    for e in evidence:
        key = (e.witness, e.epoch)
        if key in seen:
            status = 'REPLAYED_EVIDENCE' if seen[key] == e.digest else 'EQUIVOCATION'
            return ConcurrentResult(status)
        seen[key] = e.digest
    if any(e.epoch > reference[-1] for e in evidence):
        return ConcurrentResult('FUTURE_COMPETING_EPOCH')
    if any(e.epoch < reference[-1] for e in evidence):
        return ConcurrentResult('STALE_COMPETING_EPOCH')
    if any(e.digest != pinned_digest for e in evidence):
        return ConcurrentResult('DIVERGENT_DIGEST')
    base = assess_recovery(history, votes, reference=reference, returned=returned,
                           offline=offline,
                           recovery_evidence=tuple((e.witness, e.epoch) for e in evidence),
                           copies=copies, partitioned=partitioned, max_steps=max_steps)
    if base.status != 'RECOVERY_FIXTURE_UNAUTHENTICATED':
        return ConcurrentResult('BASE_' + base.status)
    return ConcurrentResult('CONCURRENT_RECOVERY_FIXTURE_UNAUTHENTICATED', len(evidence))


def safe_to_promote(*_args, **_kwargs):
    return False
