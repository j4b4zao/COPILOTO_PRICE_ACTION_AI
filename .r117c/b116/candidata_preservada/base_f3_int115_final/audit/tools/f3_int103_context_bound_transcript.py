"""F3-INT-103 offline context-bound transcript commitment.

A context label is caller supplied, not authenticated. It prevents accidental
cross-context digest equality when an independent expected digest is retained.
"""
from dataclasses import dataclass
import hashlib
import json
import re
from tools.f3_int102_transcript_commitment import commit_transcript
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b'F3_INT103_CONTEXT_BOUND_TRANSCRIPT_V1\0'
_CONTEXT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z', re.ASCII)

@dataclass(frozen=True)
class ContextBoundCommitment:
    status: str
    digest: str = ''
    context: str = ''
    transcript_digest: str = ''
    f3: str = 'OPEN'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def bind_transcript_context(segments, *, context, base_registry=None, expected_digest=None):
    """Fail closed on invalid labels, transcript errors and expected mismatches."""
    if type(context) is not str or not _CONTEXT.fullmatch(context):
        return ContextBoundCommitment('INVALID_CONTEXT')
    if expected_digest is not None and not digest_valid(expected_digest):
        return ContextBoundCommitment('INVALID_EXPECTED_CONTEXT_DIGEST')
    transcript = commit_transcript(segments, base_registry=base_registry)
    if transcript.status != 'TRANSCRIPT_FIXTURE_UNAUTHENTICATED':
        return ContextBoundCommitment('TRANSCRIPT_REJECTED:' + transcript.status)
    payload = json.dumps({'context': context, 'transcript_digest': transcript.digest},
                         sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    digest = hashlib.sha256(DOMAIN + payload).hexdigest()
    if expected_digest is not None and expected_digest != digest:
        return ContextBoundCommitment('CONTEXT_DIGEST_MISMATCH')
    return ContextBoundCommitment('CONTEXT_BOUND_FIXTURE_UNAUTHENTICATED', digest, context, transcript.digest)


def safe_to_promote(*args, **kwargs):
    return False
