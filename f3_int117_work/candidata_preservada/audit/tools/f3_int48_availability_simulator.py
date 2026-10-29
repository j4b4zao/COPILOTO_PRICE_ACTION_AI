"""INT48: bounded offline availability and quorum-evidence stress fixture.
No external evidence is authenticated. Never authorizes operational promotion.
"""
from dataclasses import dataclass
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int47_truncated_history_simulator import assess_evidence

@dataclass(frozen=True)
class AvailabilityResult:
    status: str
    checked: int = 0
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False
    consensus_verified: bool = False
    native_fencing_verified: bool = False
    orders_allowed: bool = False

def assess_availability(chain, votes, *, reference=None, copies=(), unavailable=(),
                        claimed_quorum=None, partitioned=False, max_steps=64):
    try:
        chain=tuple(chain); votes=tuple(votes); copies=tuple(copies); unavailable=frozenset(unavailable)
    except (TypeError,ValueError): return AvailabilityResult('INVALID_INPUT')
    if type(max_steps) is not int or max_steps < 2 or len(chain)>max_steps or len(copies)>max_steps:
        return AvailabilityResult('INVALID_BOUNDS')
    if len(chain)<2 or any(not isinstance(m,Membership) for m in chain):
        return AvailabilityResult('INVALID_HISTORY')
    if not isinstance(reference,tuple) or any(type(i) is not int for i in reference):
        return AvailabilityResult('MISSING_OR_INVALID_REFERENCE')
    if tuple(m.epoch for m in chain)!=reference: return AvailabilityResult('REFERENCE_MISMATCH')
    if len(votes)!=len(chain)-1: return AvailabilityResult('INCOMPLETE_VOTES')
    if claimed_quorum is not None and (type(claimed_quorum) is not int or claimed_quorum<1):
        return AvailabilityResult('INVALID_QUORUM_CLAIM')
    if any(not isinstance(x,str) or not x for x in unavailable): return AvailabilityResult('INVALID_UNAVAILABLE_SET')
    if len(set(unavailable))!=len(unavailable): return AvailabilityResult('INVALID_UNAVAILABLE_SET')
    for m in chain:
        if any(x not in m.members for x in unavailable): return AvailabilityResult('UNKNOWN_UNAVAILABLE_WITNESS')
        if len(m.members)-len(unavailable)<m.threshold: return AvailabilityResult('QUORUM_UNAVAILABLE')
        if claimed_quorum is not None and claimed_quorum!=m.threshold:
            return AvailabilityResult('MISLEADING_QUORUM_CLAIM')
    if not copies: return AvailabilityResult('MISSING_INDEPENDENT_COPIES')
    for copy in copies:
        if not isinstance(copy,tuple): return AvailabilityResult('INVALID_COPY')
        if copy!=chain: return AvailabilityResult('DIVERGENT_OR_TRUNCATED_COPY')
    if partitioned: return AvailabilityResult('PARTITION_AVAILABILITY_UNCERTAIN')
    # Identical caller-provided copies do not establish independent witnesses.
    result=assess_evidence(chain,chain,votes,votes,pinned_epochs=reference,anchor=reference,max_steps=max_steps)
    if result.status!='EVIDENCE_FIXTURE_UNAUTHENTICATED':
        return AvailabilityResult('BASE_'+result.status)
    return AvailabilityResult('AVAILABLE_FIXTURE_UNAUTHENTICATED',len(chain))

def safe_to_promote(*_args,**_kwargs): return False
