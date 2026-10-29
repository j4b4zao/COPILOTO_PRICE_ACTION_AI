"""F3-INT-38: untrusted credential lifecycle simulation. Never grants native authority.

All timestamps and issuer attestations are test fixtures, not trusted clocks or signatures.
"""
from dataclasses import dataclass
from tools.f3_int37_coordinated_attack_simulator import inspect_claim


@dataclass(frozen=True)
class CredentialFixture:
    issuer: str
    key_id: str
    generation: int
    issued_at: int
    expires_at: int
    revoked_at: int | None = None
    compromised_at: int | None = None


@dataclass(frozen=True)
class CredentialAssessment:
    status: str
    journal_matches: bool = False
    credential_eligible_in_fixture: bool = False
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False


def assess_credential(records, claim, credential, observed_at, min_generation=1, trusted_reference=None):
    """Fail closed on malformed, expired, revoked, compromised or mismatched fixtures."""
    if type(observed_at) is not int or observed_at < 0 or type(min_generation) is not int or min_generation < 1:
        return CredentialAssessment('INVALID_TIME_OR_FLOOR')
    if not isinstance(credential, CredentialFixture):
        return CredentialAssessment('MISSING_CREDENTIAL')
    c = credential
    if (not isinstance(c.issuer, str) or not c.issuer or not isinstance(c.key_id, str) or not c.key_id
        or any(type(x) is not int for x in (c.generation, c.issued_at, c.expires_at))
        or c.generation < 1 or c.issued_at < 0 or c.expires_at <= c.issued_at
        or any(x is not None and (type(x) is not int or x < 0) for x in (c.revoked_at, c.compromised_at))):
        return CredentialAssessment('INVALID_CREDENTIAL')
    try:
        inspection = inspect_claim(records, claim, trusted_reference)
    except (TypeError, ValueError, AttributeError):
        return CredentialAssessment('INVALID_CLAIM')
    if not inspection.journal_matches or inspection.status in ('REFERENCE_MISMATCH', 'INVALID_REFERENCE'):
        return CredentialAssessment('JOURNAL_OR_CLAIM_REJECTED')
    if c.issuer != claim.issuer or c.generation != claim.generation:
        return CredentialAssessment('IDENTITY_OR_GENERATION_MISMATCH', True)
    if c.generation < min_generation:
        return CredentialAssessment('ROLLBACK_GENERATION', True)
    if observed_at < c.issued_at:
        return CredentialAssessment('NOT_YET_VALID', True)
    if observed_at >= c.expires_at:
        return CredentialAssessment('EXPIRED', True)
    if c.revoked_at is not None and observed_at >= c.revoked_at:
        return CredentialAssessment('REVOKED', True)
    if c.compromised_at is not None and observed_at >= c.compromised_at:
        return CredentialAssessment('COMPROMISED', True)
    return CredentialAssessment('FIXTURE_ELIGIBLE_NOT_AUTHENTICATED', True, True)


def safe_to_promote(*_args, **_kwargs):
    return False
