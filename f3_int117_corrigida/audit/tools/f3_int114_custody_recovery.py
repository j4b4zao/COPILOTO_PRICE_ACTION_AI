"""F3-INT-114 offline reference-custody and ambiguous commit assessment.

All records are untrusted caller-provided evidence. This module does not
provision a trusted root, authenticate a witness, or authorize consumption.
"""
from dataclasses import dataclass
import re

_HEX = re.compile(r'^[0-9a-f]{64}$')
LOCKS = ('orders_allowed','live_certified','flow_complete','f3_resolved',
         'native_prototype_authorized','strict_deadline_guaranteed',
         'authenticated_witness_verified')

@dataclass(frozen=True)
class Assessment:
    status: str
    reason: str
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def assess_custody(*, retained_digest, observed_digest, custody_state,
                   independent_proof=None, generation=None, expected_generation=None):
    """Conservative, read-only comparison; claimed independence is not proof."""
    if custody_state not in ('ACTIVE', 'REVOKED', 'MISSING', 'RECOVERY_PENDING'):
        return Assessment('INVALID_CUSTODY', 'Unknown custody state')
    if custody_state != 'ACTIVE':
        return Assessment('CUSTODY_UNAVAILABLE', custody_state)
    if (not isinstance(retained_digest, str) or not _HEX.fullmatch(retained_digest)
            or not isinstance(observed_digest, str) or not _HEX.fullmatch(observed_digest)):
        return Assessment('INVALID_DIGEST', 'Invalid or absent digest')
    if (type(generation) is not int or generation < 0 or
            type(expected_generation) is not int or expected_generation < 0):
        return Assessment('INVALID_GENERATION', 'Missing or invalid generation')
    if generation != expected_generation:
        return Assessment('STALE_REFERENCE', 'Generation mismatch')
    if retained_digest != observed_digest:
        return Assessment('REFERENCE_MISMATCH', 'Digest mismatch')
    if independent_proof is None:
        return Assessment('UNAUTHENTICATED_MATCH', 'No independently authenticated custody evidence')
    return Assessment('UNVERIFIED_PROVENANCE', 'Caller supplied proof cannot be independently authenticated here')


def assess_commit_recovery(*, ack_state, store_state, retained_pin_state,
                           competing_writer=False, stable_snapshot=False):
    """No retry or second consumption; uncertain outcomes remain unresolved."""
    if ack_state not in ('RECEIVED', 'LOST', 'UNKNOWN'):
        return Assessment('INVALID_ACK', 'Invalid acknowledgement state')
    if store_state not in ('COMMITTED', 'NOT_COMMITTED', 'UNAVAILABLE', 'CONFLICT'):
        return Assessment('INVALID_STORE', 'Invalid store observation')
    if retained_pin_state not in ('MATCH', 'STALE', 'MISSING', 'REVOKED', 'UNKNOWN'):
        return Assessment('INVALID_PIN', 'Invalid retained pin state')
    if type(competing_writer) is not bool or type(stable_snapshot) is not bool:
        return Assessment('INVALID_OBSERVATION', 'Boolean observation required')
    if competing_writer or not stable_snapshot:
        return Assessment('CONCURRENT_OR_TOCTOU_UNRESOLVED', 'No atomic cross-boundary observation')
    if retained_pin_state != 'MATCH':
        return Assessment('PIN_UNRESOLVED', 'Pin cannot establish state')
    if store_state in ('UNAVAILABLE', 'CONFLICT'):
        return Assessment('STORE_UNRESOLVED', 'Store unavailable or conflicting')
    if ack_state != 'RECEIVED':
        return Assessment('ACK_UNRESOLVED', 'Do not retry blindly or consume twice')
    if store_state == 'NOT_COMMITTED':
        return Assessment('NO_COMMIT_OBSERVED', 'Observation only, not retry authority')
    return Assessment('COMMIT_OBSERVED_UNAUTHENTICATED', 'Observation only, no operational authority')


def assess_durability(*, event, independently_verified=False):
    """Offline evidence cannot certify persistence through hardware loss."""
    if event not in ('PROCESS_CRASH', 'OS_SHUTDOWN', 'POWER_LOSS', 'MEDIA_LOSS'):
        return Assessment('INVALID_EVENT', 'Unknown failure event')
    if type(independently_verified) is not bool:
        return Assessment('INVALID_VERIFICATION', 'Invalid verification field')
    if event == 'PROCESS_CRASH':
        return Assessment('PROCESS_RECOVERY_UNATTESTED', 'Process-only model cannot certify storage durability')
    return Assessment('PHYSICAL_DURABILITY_UNPROVEN', 'Offline simulation does not establish hardware durability')


def safe_to_promote(*args, **kwargs):
    return False
