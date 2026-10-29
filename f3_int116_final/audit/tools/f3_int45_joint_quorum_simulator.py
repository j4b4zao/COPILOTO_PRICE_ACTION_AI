"""F3-INT-45: offline joint-membership quorum intersection fixtures only.

Membership, votes, partitions, and pins are caller-controlled; NOT signatures,
independent witnesses, consensus, durable fencing, or operational authority.
"""
from dataclasses import dataclass
from tools.f3_int44_witness_membership_simulator import Membership

@dataclass(frozen=True)
class JointResult:
    status: str
    overlap: tuple = ()
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False
    consensus_verified: bool = False

def _valid(m):
    return (isinstance(m, Membership) and type(m.epoch) is int and m.epoch > 0
            and type(m.predecessor) is int and 0 <= m.predecessor < m.epoch
            and isinstance(m.members, tuple) and len(m.members) > 0
            and all(isinstance(x, str) and x for x in m.members)
            and len(set(m.members)) == len(m.members)
            and type(m.threshold) is int and 1 <= m.threshold <= len(m.members))

def assess_joint(old, new, left_votes, right_votes, *, pinned_epochs=None,
                 partitioned=False, compromised=(), suspected_collusion=()):
    if not _valid(old) or not _valid(new):
        return JointResult('INVALID_MEMBERSHIP')
    if pinned_epochs is None:
        return JointResult('UNPINNED_TRANSITION')
    if (not isinstance(pinned_epochs, tuple) or len(pinned_epochs) != 2 or
        any(type(e) is not int for e in pinned_epochs)):
        return JointResult('INVALID_PIN')
    if pinned_epochs != (old.epoch, new.epoch):
        return JointResult('PIN_MISMATCH')
    if new.epoch <= old.epoch or new.predecessor != old.epoch:
        return JointResult('BROKEN_TRANSITION')
    try:
        lv, rv = tuple(left_votes), tuple(right_votes)
        compromised = frozenset(compromised)
        groups = tuple(tuple(g) for g in suspected_collusion)
    except (TypeError, ValueError):
        return JointResult('INVALID_INPUT')
    if (any(not isinstance(x, str) or not x for x in lv + rv) or
        len(set(lv)) != len(lv) or len(set(rv)) != len(rv)):
        return JointResult('INVALID_VOTES')
    if set(lv) - set(old.members) or set(rv) - set(new.members):
        return JointResult('NON_MEMBER_VOTE')
    if compromised.intersection(lv + rv):
        return JointResult('COMPROMISED_VOTER')
    if any(len(set(g).intersection(lv + rv)) > 1 for g in groups):
        return JointResult('SUSPECTED_COLLUSION')
    overlap = tuple(sorted(set(old.members).intersection(new.members)))
    if not overlap:
        return JointResult('DISJOINT_MEMBERSHIP')
    if len(lv) < old.threshold or len(rv) < new.threshold:
        return JointResult('INSUFFICIENT_JOINT_VOTES', overlap)
    # All *possible* old/new quorums intersect iff min intersection >= 1.
    # Bound for minimum possible intersection of two quorums across universe.
    universe = len(set(old.members).union(new.members))
    minimum = max(0, old.threshold + new.threshold - universe)
    if minimum == 0:
        return JointResult('QUORUM_INTERSECTION_NOT_GUARANTEED', overlap)
    if not set(lv).intersection(rv):
        return JointResult('OBSERVED_QUORUM_DISJOINT', overlap)
    if partitioned:
        return JointResult('PARTITION_CONTESTED_UNAUTHENTICATED', overlap)
    return JointResult('JOINT_FIXTURE_UNAUTHENTICATED', overlap)

def safe_to_promote(*_args, **_kwargs):
    return False
