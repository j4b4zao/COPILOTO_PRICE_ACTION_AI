"""F3-INT-44: offline adversarial witness membership model, NOT authenticated quorum."""
from dataclasses import dataclass
from tools.f3_int43_partition_reconciliation_simulator import reconcile_partition, Witness

@dataclass(frozen=True)
class Membership:
    epoch: int
    members: tuple
    threshold: int
    predecessor: int = 0

@dataclass(frozen=True)
class MembershipResult:
    status: str
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False
    independent_verified: bool = False

def assess_membership(left, right, witnesses, membership, *, pinned_epoch=None, compromised=(), suspected_collusion=()):
    """Caller-controlled fixture metadata; all positive outcomes are untrusted."""
    try:
        witnesses = tuple(witnesses)
        compromised = frozenset(compromised)
        suspected_collusion = tuple(tuple(g) for g in suspected_collusion)
    except (TypeError, ValueError):
        return MembershipResult('INVALID_INPUT')
    if (not isinstance(membership, Membership) or type(membership.epoch) is not int
        or membership.epoch < 1 or type(membership.predecessor) is not int
        or membership.predecessor < 0 or membership.predecessor >= membership.epoch
        or not isinstance(membership.members, tuple)
        or not membership.members or any(not isinstance(m,str) or not m for m in membership.members)
        or len(set(membership.members)) != len(membership.members)
        or type(membership.threshold) is not int or not 1 <= membership.threshold <= len(membership.members)):
        return MembershipResult('INVALID_MEMBERSHIP')
    if pinned_epoch is None:
        return MembershipResult('UNPINNED_MEMBERSHIP')
    if type(pinned_epoch) is not int or pinned_epoch < 1:
        return MembershipResult('INVALID_PIN')
    if membership.epoch != pinned_epoch:
        return MembershipResult('MEMBERSHIP_EPOCH_MISMATCH')
    if any(not isinstance(w,Witness) for w in witnesses):
        return MembershipResult('INVALID_WITNESS')
    ids = [w.identity for w in witnesses]
    if len(ids) != len(set(ids)):
        return MembershipResult('DUPLICATE_WITNESS_IDENTITY')
    if any(i not in membership.members for i in ids):
        return MembershipResult('NON_MEMBER_WITNESS')
    if compromised.intersection(ids):
        return MembershipResult('COMPROMISED_WITNESS')
    if any(len(set(g).intersection(ids)) > 1 for g in suspected_collusion):
        return MembershipResult('SUSPECTED_COLLUSION')
    if len(ids) < membership.threshold:
        return MembershipResult('INSUFFICIENT_FIXTURE_VOTES')
    base = reconcile_partition(left,right,witnesses)
    if base.status != 'AGREED_FIXTURE_UNAUTHENTICATED':
        return MembershipResult('BASE_' + base.status)
    return MembershipResult('QUORUM_FIXTURE_UNAUTHENTICATED')

def safe_to_promote(*_args, **_kwargs):
    return False
