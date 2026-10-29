"""F3-INT-37: adversarial, in-memory trust-boundary simulation only.

A digest is NOT a signature. A claimed issuer is NOT authenticated.
No record, witness, quorum, or attestation in this module authorizes closure.
"""
from dataclasses import dataclass
from tools.f3_int34_persistence_simulator import replay
from tools.f3_int36_anchor_rollback_simulator import Anchor, assess_copy


@dataclass(frozen=True)
class ClaimedAnchor:
    anchor: Anchor
    issuer: str
    generation: int
    authenticated: bool = False


@dataclass(frozen=True)
class TrustAssessment:
    status: str
    journal_matches: bool
    issuer_authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False


def inspect_claim(records, claim, trusted_reference=None):
    """Evaluate untrusted claims; reference is assumed, never authenticated here."""
    if not isinstance(claim, ClaimedAnchor) or not isinstance(claim.issuer, str) or not claim.issuer:
        return TrustAssessment('INVALID_CLAIM', False)
    if type(claim.generation) is not int or claim.generation < 1:
        return TrustAssessment('INVALID_GENERATION', False)
    try:
        replay(tuple(records))
        result = assess_copy(records, claim.anchor)
    except (ValueError, TypeError, AttributeError):
        return TrustAssessment('INVALID_JOURNAL_OR_ANCHOR', False)
    if not result.matched:
        return TrustAssessment(result.status, False)
    if trusted_reference is None:
        return TrustAssessment('UNAUTHENTICATED_CLAIM', True)
    if not isinstance(trusted_reference, ClaimedAnchor):
        return TrustAssessment('INVALID_REFERENCE', True)
    if claim != trusted_reference:
        return TrustAssessment('REFERENCE_MISMATCH', True)
    return TrustAssessment('REFERENCE_MATCH_NOT_AUTHENTICATED', True)


def coordinated_rewrite(records, events, writer='attacker'):
    """Demonstrate an attacker can rebuild a self-consistent hash chain."""
    from tools.f3_int34_persistence_simulator import Authority
    authority = Authority()
    epoch = authority.lease(writer)
    for event in events:
        authority.append(writer, epoch, event)
    return authority.snapshot()


def requirements_for_authenticated_anchor():
    return (
        'independently authenticated issuer and key lifecycle',
        'anti-rollback monotonic generation from independent trusted authority',
        'session and job binding plus freshness and causal ordering',
        'revocation and compromise recovery with fail-closed policy',
        'independent witness and durable evidence with verified provenance',
        'native integration and adversarial process-level validation',
    )


def safe_to_promote(*_args, **_kwargs):
    return False
