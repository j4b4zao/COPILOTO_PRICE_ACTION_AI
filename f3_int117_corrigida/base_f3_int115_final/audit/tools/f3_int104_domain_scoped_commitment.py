"""F3-INT-104 offline purpose-scoped commitment; no authentication or authorization."""
from dataclasses import dataclass
import hashlib
import json
import re
from tools.f3_int103_context_bound_transcript import bind_transcript_context
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b"F3_INT104_PURPOSE_SCOPED_COMMITMENT_V1\0"
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z", re.ASCII)

@dataclass(frozen=True)
class ScopedCommitment:
    status: str
    digest: str = ""
    context_digest: str = ""
    purpose: str = ""
    run_id: str = ""
    revision: int = 0
    f3: str = "OPEN"
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def scope_transcript(segments, *, context, purpose, run_id, revision, base_registry=None, expected_digest=None):
    """Fail closed; labels and expected hash are caller-supplied, never trusted."""
    if type(purpose) is not str or not LABEL.fullmatch(purpose):
        return ScopedCommitment("INVALID_PURPOSE")
    if type(run_id) is not str or not LABEL.fullmatch(run_id):
        return ScopedCommitment("INVALID_RUN_ID")
    if type(revision) is not int or not 0 <= revision <= 2147483647:
        return ScopedCommitment("INVALID_REVISION")
    if expected_digest is not None and not digest_valid(expected_digest):
        return ScopedCommitment("INVALID_EXPECTED_DIGEST")
    parent = bind_transcript_context(segments, context=context, base_registry=base_registry)
    if parent.status != "CONTEXT_BOUND_FIXTURE_UNAUTHENTICATED":
        return ScopedCommitment("PARENT_REJECTED:" + parent.status)
    canonical = json.dumps({"parent_digest":parent.digest,"purpose":purpose,"run_id":run_id,
                            "revision":revision},sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")
    digest = hashlib.sha256(DOMAIN+canonical).hexdigest()
    if expected_digest is not None and digest != expected_digest:
        return ScopedCommitment("SCOPED_DIGEST_MISMATCH")
    return ScopedCommitment("SCOPED_FIXTURE_UNAUTHENTICATED",digest,parent.digest,purpose,run_id,revision)


def safe_to_promote(*args, **kwargs):
    return False
