"""F3-INT-40: purely in-memory concurrent rotation/revocation evidence checker.

This fixture is NOT a distributed consensus protocol, signature verifier, or authority.
"""
from dataclasses import dataclass
from tools.f3_int39_key_rotation_simulator import RotationEvent, assess_rotation

@dataclass(frozen=True)
class AuthorityEvent:
    authority_id: str
    parent: str
    event_id: str
    event: RotationEvent

@dataclass(frozen=True)
class ConcurrentAssessment:
    status: str
    fixture_eligible: bool = False
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False


def assess_concurrent_rotation(records, claim, credential, events, observed_at,
                               min_generation=1, trusted_reference=None):
    """Fail closed if events do not form one causally linked authority history.

    Parent IDs model a single chain, NOT an authenticated provenance or consensus.
    """
    try:
        events = tuple(events)
    except TypeError:
        return ConcurrentAssessment('INVALID_EVENTS')
    if any(not isinstance(x, AuthorityEvent) or not isinstance(x.authority_id, str)
           or not x.authority_id or not isinstance(x.event_id, str) or not x.event_id
           or not isinstance(x.parent, str) or not isinstance(x.event, RotationEvent)
           for x in events):
        return ConcurrentAssessment('INVALID_EVENTS')
    ids = [x.event_id for x in events]
    if len(set(ids)) != len(ids):
        return ConcurrentAssessment('DUPLICATE_EVENT_ID')
    by_id = {x.event_id: x for x in events}
    if any(x.parent and x.parent not in by_id for x in events):
        return ConcurrentAssessment('MISSING_CAUSAL_PARENT')
    children = {}
    for x in events:
        children.setdefault(x.parent, []).append(x.event_id)
    if len(children.get('', [])) != 1 or any(len(v) > 1 for v in children.values()):
        return ConcurrentAssessment('DIVERGENT_AUTHORITY_HISTORY')
    ordered = []
    seen = set()
    current = children[''][0]
    while current:
        if current in seen:
            return ConcurrentAssessment('CAUSAL_CYCLE')
        seen.add(current)
        ordered.append(by_id[current])
        current = children.get(current, [None])[0]
    if len(seen) != len(events):
        return ConcurrentAssessment('DISCONNECTED_HISTORY')
    # Explicit handoff events are not modeled; changing writers is not sufficient
    # evidence of a fenced old writer, so reject instead of assuming authority.
    if len({x.authority_id for x in ordered}) > 1:
        return ConcurrentAssessment('UNPROVEN_AUTHORITY_HANDOFF')
    result = assess_rotation(records, claim, credential, [x.event for x in ordered],
                             observed_at, min_generation, trusted_reference)
    return ConcurrentAssessment(result.status, result.fixture_eligible)


def safe_to_promote(*_args, **_kwargs):
    return False
