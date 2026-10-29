"""F3-INT-39: untrusted, in-memory key rotation fixture; no real cryptography or authority."""
from dataclasses import dataclass
from tools.f3_int38_credential_lifecycle_simulator import CredentialFixture, assess_credential


@dataclass(frozen=True)
class RotationEvent:
    kind: str
    key_id: str
    at: int
    sequence: int


@dataclass(frozen=True)
class RotationAssessment:
    status: str
    fixture_eligible: bool = False
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False


def assess_rotation(records, claim, credential, events, observed_at, min_generation=1, trusted_reference=None):
    """Fail closed on event disorder, conflicting key state, revocation, or stale evidence."""
    base = assess_credential(records, claim, credential, observed_at, min_generation, trusted_reference)
    if not base.credential_eligible_in_fixture:
        return RotationAssessment('BASE_' + base.status)
    try:
        events = tuple(events)
    except TypeError:
        return RotationAssessment('INVALID_EVENTS')
    if not isinstance(credential, CredentialFixture):
        return RotationAssessment('INVALID_CREDENTIAL')
    if any(not isinstance(e, RotationEvent) or e.kind not in ('ACTIVATE', 'REVOKE', 'COMPROMISE')
           or not isinstance(e.key_id, str) or not e.key_id or type(e.at) is not int or e.at < 0
           or type(e.sequence) is not int or e.sequence < 1 for e in events):
        return RotationAssessment('INVALID_EVENTS')
    if len({e.sequence for e in events}) != len(events):
        return RotationAssessment('DUPLICATE_SEQUENCE')
    if any(a.sequence >= b.sequence or a.at > b.at for a, b in zip(events, events[1:])):
        return RotationAssessment('OUT_OF_ORDER')
    if any(e.at > observed_at for e in events):
        return RotationAssessment('FUTURE_EVENT')
    active = None
    retired = set()
    for e in events:
        if e.kind == 'ACTIVATE':
            if e.key_id in retired:
                return RotationAssessment('REACTIVATION_FORBIDDEN')
            if active is not None and active != e.key_id:
                retired.add(active)
            active = e.key_id
        else:
            retired.add(e.key_id)
            if active == e.key_id:
                active = None
    if credential.key_id in retired:
        return RotationAssessment('KEY_RETIRED')
    if active != credential.key_id:
        return RotationAssessment('KEY_NOT_ACTIVE')
    return RotationAssessment('FIXTURE_ROTATION_ELIGIBLE_NOT_AUTHENTICATED', True)


def safe_to_promote(*_args, **_kwargs):
    return False
