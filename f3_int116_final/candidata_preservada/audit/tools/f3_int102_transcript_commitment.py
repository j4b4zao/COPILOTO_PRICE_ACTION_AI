"""F3-INT-102: offline cross-batch transcript commitment and strict verification.

Caller-supplied expected digest is not a trusted anchor. No authentication.
"""
from dataclasses import dataclass
import hashlib
import json
from tools.f3_int101_cross_batch_audit import audit_cross_batch, AuditSegment
from tools.f3_int98_policy_bundle_registry import PolicyEvidenceRegistry, valid_policy_registry
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b"F3_INT102_TRANSCRIPT_COMMITMENT_V1\0"

@dataclass(frozen=True)
class TranscriptCommitment:
    status: str
    digest: str = ""
    combined_tip: str = ""
    count: int = 0
    f3: str = "OPEN"
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def commit_transcript(segments, *, base_registry=None, expected_digest=None):
    """Bind all segment boundaries and per-record hashes to a canonical digest.

    This is stronger *coverage* than the INT101 tip alone, not stronger trust.
    """
    if base_registry is None:
        base_registry = PolicyEvidenceRegistry()
    if not valid_policy_registry(base_registry):
        return TranscriptCommitment("INVALID_TRANSCRIPT_BASE")
    if expected_digest is not None and not digest_valid(expected_digest):
        return TranscriptCommitment("INVALID_TRANSCRIPT_EXPECTED_DIGEST")
    result = audit_cross_batch(segments, base_registry=base_registry)
    if result.status != "CROSS_BATCH_FIXTURE_UNAUTHENTICATED":
        return TranscriptCommitment("TRANSCRIPT_AUDIT_REJECTED:" + result.status)
    payload = {"base": list(base_registry.reference_ids), "combined_tip": result.combined_tip,
               "segments": []}
    for segment in segments:
        # INT101 has already validated all types, receipts and registry prefixes.
        payload["segments"].append({
            "registry": list(segment.registry.reference_ids),
            "expected_tip": segment.expected_tip,
            "records": [{"sha256": r.sha256, "length": len(r.blob)} for r in segment.records],
            "receipts": [{"reference_id": r.reference_id, "classification": r.classification}
                         for r in segment.receipts]})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    digest = hashlib.sha256(DOMAIN + canonical).hexdigest()
    if expected_digest is not None and expected_digest != digest:
        return TranscriptCommitment("TRANSCRIPT_DIGEST_MISMATCH")
    return TranscriptCommitment("TRANSCRIPT_FIXTURE_UNAUTHENTICATED", digest, result.combined_tip, len(segments))


def safe_to_promote(*args, **kwargs):
    return False
