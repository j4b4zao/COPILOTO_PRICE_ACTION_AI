"""F3-INT-49: offline return-from-outage and replay checks; no real witnesses."""
from dataclasses import dataclass
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int47_truncated_history_simulator import assess_evidence

@dataclass(frozen=True)
class RecoveryResult:
    status: str
    checked: int = 0
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False
    consensus_verified: bool = False
    native_fencing_verified: bool = False
    orders_allowed: bool = False

def assess_recovery(history, votes, *, reference=None, returned=(), offline=(),
                    recovery_evidence=(), copies=(), partitioned=False, max_steps=64):
    try:
        history=tuple(history); votes=tuple(votes); returned=tuple(returned)
        offline=tuple(offline); recovery_evidence=tuple(recovery_evidence); copies=tuple(copies)
    except (TypeError, ValueError): return RecoveryResult('INVALID_INPUT')
    if type(max_steps) is not int or max_steps<2 or len(history)>max_steps or len(copies)>max_steps:
        return RecoveryResult('INVALID_BOUNDS')
    if len(history)<2 or any(not isinstance(m,Membership) for m in history):
        return RecoveryResult('INVALID_HISTORY')
    if not isinstance(reference,tuple) or any(type(x) is not int for x in reference):
        return RecoveryResult('MISSING_OR_INVALID_REFERENCE')
    epochs=tuple(m.epoch for m in history)
    if epochs != reference: return RecoveryResult('REFERENCE_MISMATCH')
    if len(votes)!=len(history)-1: return RecoveryResult('INCOMPLETE_VOTES')
    if any(not isinstance(x,str) or not x for x in returned+offline):
        return RecoveryResult('INVALID_WITNESS_ID')
    if len(set(returned))!=len(returned) or len(set(offline))!=len(offline):
        return RecoveryResult('DUPLICATE_WITNESS')
    if set(returned)&set(offline): return RecoveryResult('CONTRADICTORY_AVAILABILITY')
    if any(x not in history[-1].members for x in returned+offline):
        return RecoveryResult('UNKNOWN_WITNESS')
    if not returned: return RecoveryResult('NO_RETURNED_WITNESS')
    # Evidence tuples are (witness_id, observed_epoch), never signatures.
    if any(not isinstance(x,tuple) or len(x)!=2 or not isinstance(x[0],str)
           or type(x[1]) is not int for x in recovery_evidence):
        return RecoveryResult('INVALID_RECOVERY_EVIDENCE')
    ids=[x[0] for x in recovery_evidence]
    if len(set(ids))!=len(ids): return RecoveryResult('REPLAYED_WITNESS_EVIDENCE')
    if set(ids)!=set(returned): return RecoveryResult('MISSING_OR_EXTRA_EVIDENCE')
    if any(epoch<reference[-1] for _,epoch in recovery_evidence):
        return RecoveryResult('STALE_REPLAYED_EVIDENCE')
    if any(epoch>reference[-1] for _,epoch in recovery_evidence):
        return RecoveryResult('FUTURE_UNPINNED_EVIDENCE')
    if len(history[-1].members)-len(offline)<history[-1].threshold:
        return RecoveryResult('QUORUM_STILL_UNAVAILABLE')
    if not copies: return RecoveryResult('MISSING_COPIES')
    if any(not isinstance(c,tuple) for c in copies): return RecoveryResult('INVALID_COPY')
    if any(c!=history for c in copies): return RecoveryResult('DIVERGENT_OR_TRUNCATED_COPY')
    if partitioned: return RecoveryResult('PARTITION_UNRESOLVED')
    base=assess_evidence(history,history,votes,votes,pinned_epochs=reference,
                         anchor=reference,max_steps=max_steps)
    if base.status!='EVIDENCE_FIXTURE_UNAUTHENTICATED':
        return RecoveryResult('BASE_'+base.status)
    return RecoveryResult('RECOVERY_FIXTURE_UNAUTHENTICATED',len(history))

def safe_to_promote(*_args,**_kwargs): return False
