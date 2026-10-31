"""F3-INT-106 offline typed batch manifest; local consistency only."""
from dataclasses import dataclass
import hashlib
import json
from a6_vendor.tools.f3_int105_typed_identity_envelope import typed_envelope
from a6_vendor.tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b"F3_INT106_TYPED_BATCH_MANIFEST_V1\0"

@dataclass(frozen=True)
class TypedBatchEntry:
    kind: str
    subject: str

@dataclass(frozen=True)
class TypedBatchManifest:
    status: str
    digest: str = ""
    entries: tuple = ()
    f3: str = "OPEN"
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False

def build_typed_batch(segments, *, context, purpose, run_id, revision, entries, base_registry=None, expected_digest=None):
    """Bind an ordered, unique set of typed evidence identities to one scope.

    Digest comparison is not origin authentication. Reject duplicates rather than
    silently deduplicating. No IO or external effects.
    """
    if type(entries) is not tuple or not 1 <= len(entries) <= 32 or any(type(e) is not TypedBatchEntry for e in entries):
        return TypedBatchManifest("INVALID_ENTRIES")
    if expected_digest is not None and not digest_valid(expected_digest):
        return TypedBatchManifest("INVALID_EXPECTED_DIGEST")
    identities = set()
    digests = set()
    manifest = []
    for entry in entries:
        if (entry.kind, entry.subject) in identities:
            return TypedBatchManifest("DUPLICATE_TYPED_IDENTITY")
        item = typed_envelope(segments, context=context, purpose=purpose, run_id=run_id,
                              revision=revision, kind=entry.kind, subject=entry.subject,
                              base_registry=base_registry)
        if item.status != "TYPED_FIXTURE_UNAUTHENTICATED":
            return TypedBatchManifest("ENTRY_REJECTED:" + item.status)
        if item.digest in digests:
            return TypedBatchManifest("DUPLICATE_ENTRY_DIGEST")
        identities.add((entry.kind, entry.subject))
        digests.add(item.digest)
        manifest.append({"kind": entry.kind, "subject": entry.subject, "digest": item.digest})
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    digest = hashlib.sha256(DOMAIN + payload).hexdigest()
    if expected_digest is not None and expected_digest != digest:
        return TypedBatchManifest("BATCH_DIGEST_MISMATCH")
    return TypedBatchManifest("BATCH_FIXTURE_UNAUTHENTICATED", digest, tuple(entries))

def safe_to_promote(*args, **kwargs):
    return False
