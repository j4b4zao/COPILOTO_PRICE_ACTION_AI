"""F3-INT-105: offline typed identity envelope, never an authentication proof."""
from dataclasses import dataclass
import hashlib
import json
import re
from a6_vendor.tools.f3_int104_domain_scoped_commitment import scope_transcript
from a6_vendor.tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b"F3_INT105_TYPED_IDENTITY_ENVELOPE_V1\0"
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z", re.ASCII)
KINDS = frozenset(("audit", "replay", "report"))

@dataclass(frozen=True)
class TypedEnvelope:
    status: str
    digest: str = ""
    scoped_digest: str = ""
    kind: str = ""
    subject: str = ""
    f3: str = "OPEN"
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False

def typed_envelope(segments, *, context, purpose, run_id, revision, kind, subject, base_registry=None, expected_digest=None):
    """Reject noncanonical Unicode and unrecognized types, bind typed identity to prior scope."""
    if type(kind) is not str or kind not in KINDS:
        return TypedEnvelope("INVALID_KIND")
    if type(subject) is not str or not LABEL.fullmatch(subject):
        return TypedEnvelope("INVALID_SUBJECT")
    if expected_digest is not None and not digest_valid(expected_digest):
        return TypedEnvelope("INVALID_EXPECTED_DIGEST")
    parent = scope_transcript(segments, context=context, purpose=purpose, run_id=run_id,
                              revision=revision, base_registry=base_registry)
    if parent.status != "SCOPED_FIXTURE_UNAUTHENTICATED":
        return TypedEnvelope("PARENT_REJECTED:" + parent.status)
    # Distinct JSON keys and a domain tag avoid field-order and role confusion.
    payload = json.dumps({"kind": kind, "subject": subject, "scoped_digest": parent.digest},
                         sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    digest = hashlib.sha256(DOMAIN + payload).hexdigest()
    if expected_digest is not None and digest != expected_digest:
        return TypedEnvelope("TYPED_DIGEST_MISMATCH")
    return TypedEnvelope("TYPED_FIXTURE_UNAUTHENTICATED", digest, parent.digest, kind, subject)

def safe_to_promote(*args, **kwargs):
    return False
