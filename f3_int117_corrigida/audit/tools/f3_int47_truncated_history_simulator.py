"""F3-INT-47: bounded adversarial evidence comparison, offline fixtures only.

All supplied anchors, membership and votes are untrusted. Matching caller-supplied
pins or quorum records never establish authentication, durable consensus or authority.
"""
from dataclasses import dataclass
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int46_multiepoch_simulator import audit_epochs

@dataclass(frozen=True)
class EvidenceResult:
    status: str
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False
    consensus_verified: bool = False
    native_fencing_verified: bool = False

def assess_evidence(left, right, left_votes, right_votes, *, pinned_epochs=None,
                    anchor=None, partitioned=False, compromised=(),
                    suspected_collusion=(), max_steps=64):
    try:
        a,b=tuple(left),tuple(right)
        va,vb=tuple(left_votes),tuple(right_votes)
    except (TypeError,ValueError):
        return EvidenceResult('INVALID_INPUT')
    if not a or not b or any(not isinstance(x,Membership) for x in a+b):
        return EvidenceResult('INVALID_HISTORY')
    if type(max_steps) is not int or max_steps < 2 or max(len(a),len(b)) > max_steps:
        return EvidenceResult('INVALID_BOUNDS')
    if pinned_epochs is None or anchor is None:
        return EvidenceResult('MISSING_EXTERNAL_REFERENCE')
    if not isinstance(pinned_epochs,tuple) or not isinstance(anchor,tuple) or any(type(x) is not int for x in pinned_epochs+anchor):
        return EvidenceResult('INVALID_REFERENCE')
    if anchor != pinned_epochs:
        return EvidenceResult('ANCHOR_PIN_CONFLICT')
    ea=tuple(x.epoch for x in a); eb=tuple(x.epoch for x in b)
    if ea != pinned_epochs or eb != pinned_epochs:
        if (len(ea) < len(pinned_epochs) and ea == pinned_epochs[:len(ea)]) or (len(eb) < len(pinned_epochs) and eb == pinned_epochs[:len(eb)]):
            return EvidenceResult('TRUNCATED_HISTORY')
        return EvidenceResult('HISTORY_PIN_CONFLICT')
    if a != b:
        return EvidenceResult('DIVERGENT_MEMBERSHIP')
    if va != vb:
        return EvidenceResult('COORDINATED_VOTE_CONFLICT')
    outcome=audit_epochs(a,va,pinned_epochs=pinned_epochs,partitioned=partitioned,
                         compromised=compromised,suspected_collusion=suspected_collusion,
                         max_steps=max_steps)
    if outcome.status != 'CHAIN_FIXTURE_UNAUTHENTICATED':
        return EvidenceResult(outcome.status)
    # Adjacent checks alone cannot certify non-adjacent quorum intersections.
    for i in range(len(a)):
        for j in range(i+2,len(a)):
            old,new=a[i],a[j]
            universe=len(set(old.members)|set(new.members))
            if old.threshold+new.threshold <= universe:
                return EvidenceResult('NONADJACENT_QUORUM_GAP')
    return EvidenceResult('EVIDENCE_FIXTURE_UNAUTHENTICATED')

def safe_to_promote(*_args,**_kwargs):
    return False
