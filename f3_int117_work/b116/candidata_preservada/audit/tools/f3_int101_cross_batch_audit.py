"""F3-INT-101: read-only cross-batch fixture lineage audit.

All evidence is caller-supplied, offline and unauthenticated. The returned digest
is a consistency checksum, not an externally authenticated witness or signature.
"""
from dataclasses import dataclass
import hashlib
from tools.f3_int98_policy_bundle_registry import PolicyEvidenceRegistry, valid_policy_registry
from tools.f3_int100_receipt_lineage import verify_receipt_lineage
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b'F3_INT101_CROSS_BATCH_FIXTURE_V1\0'

@dataclass(frozen=True)
class AuditSegment:
    records: tuple
    receipts: tuple
    registry: PolicyEvidenceRegistry
    expected_tip: str

@dataclass(frozen=True)
class CrossBatchAudit:
    status: str
    tips: tuple = ()
    combined_tip: str = ''
    f3: str = 'OPEN'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def audit_cross_batch(segments, *, base_registry=None, expected_combined_tip=None):
    """Re-evaluate every segment and enforce exact prefix continuity.

    expected_combined_tip is a caller-provided comparison value, NOT a trust root.
    """
    if base_registry is None:
        base_registry = PolicyEvidenceRegistry()
    if not valid_policy_registry(base_registry):
        return CrossBatchAudit('INVALID_CROSS_BATCH_BASE')
    if type(segments) is not tuple or not 1 <= len(segments) <= 16 or any(type(s) is not AuditSegment for s in segments):
        return CrossBatchAudit('INVALID_CROSS_BATCH_SEGMENTS')
    if expected_combined_tip is not None and not digest_valid(expected_combined_tip):
        return CrossBatchAudit('INVALID_CROSS_BATCH_EXPECTED_TIP')
    previous = base_registry
    state = hashlib.sha256(DOMAIN + b'BASE\0' + b''.join(x.encode('ascii') + b'\0' for x in previous.reference_ids)).digest()
    tips = []
    for index, segment in enumerate(segments):
        if not valid_policy_registry(segment.registry):
            return CrossBatchAudit('INVALID_CROSS_BATCH_REGISTRY')
        if not digest_valid(segment.expected_tip):
            return CrossBatchAudit('INVALID_CROSS_BATCH_SEGMENT_TIP')
        result = verify_receipt_lineage(segment.records, segment.receipts, segment.registry,
                                        segment.expected_tip, base_registry=previous)
        if result.status != 'LINEAGE_FIXTURE_UNAUTHENTICATED':
            return CrossBatchAudit('CROSS_BATCH_SEGMENT_REJECTED:' + result.status)
        state = hashlib.sha256(DOMAIN + state + index.to_bytes(2, 'big') + bytes.fromhex(result.tip)).digest()
        tips.append(result.tip)
        previous = segment.registry
    combined = state.hex()
    if expected_combined_tip is not None and expected_combined_tip != combined:
        return CrossBatchAudit('CROSS_BATCH_COMBINED_TIP_MISMATCH')
    return CrossBatchAudit('CROSS_BATCH_FIXTURE_UNAUTHENTICATED', tuple(tips), combined)


def safe_to_promote(*args, **kwargs):
    return False
