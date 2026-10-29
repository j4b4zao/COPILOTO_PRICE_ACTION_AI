"""F3-INT-107: offline, deterministic cross-batch continuity commitments.

These hashes are local consistency checks, NOT origin authentication.
"""
from dataclasses import dataclass
import hashlib
import json
from tools.f3_int106_typed_batch_manifest import build_typed_batch
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b"F3_INT107_TYPED_BATCH_CHAIN_V1\0"
GENESIS = "0" * 64

@dataclass(frozen=True)
class ChainBatch:
    entries: tuple
    revision: int

@dataclass(frozen=True)
class ChainResult:
    status: str
    digest: str = ""
    batch_digests: tuple = ()
    f3: str = "OPEN"
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False

def build_typed_chain(segments, *, context, purpose, run_id, batches, base_registry=None,
                      expected_digest=None, expected_batch_digests=None):
    """Recompute each typed batch, bind its index and revision to predecessor.

    Revision must be strictly increasing (not necessarily consecutive). Reject
    duplicate/reordered batches and any mismatch against supplied expectations.
    """
    if type(batches) is not tuple or not 1 <= len(batches) <= 16 or any(type(b) is not ChainBatch for b in batches):
        return ChainResult("INVALID_BATCHES")
    if expected_digest is not None and not digest_valid(expected_digest):
        return ChainResult("INVALID_EXPECTED_DIGEST")
    if expected_batch_digests is not None:
        if type(expected_batch_digests) is not tuple or len(expected_batch_digests) != len(batches) or any(not digest_valid(d) for d in expected_batch_digests):
            return ChainResult("INVALID_EXPECTED_BATCH_DIGESTS")
    previous_revision = -1
    previous = GENESIS
    digests = []
    seen = set()
    for index, batch in enumerate(batches):
        if type(batch.revision) is not int or batch.revision < 0 or batch.revision <= previous_revision:
            return ChainResult("INVALID_REVISION_SEQUENCE")
        result = build_typed_batch(segments, context=context, purpose=purpose, run_id=run_id,
                                   revision=batch.revision, entries=batch.entries, base_registry=base_registry)
        if result.status != "BATCH_FIXTURE_UNAUTHENTICATED":
            return ChainResult("BATCH_REJECTED:" + result.status)
        if result.digest in seen:
            return ChainResult("DUPLICATE_BATCH_DIGEST")
        if expected_batch_digests is not None and result.digest != expected_batch_digests[index]:
            return ChainResult("BATCH_DIGEST_MISMATCH")
        payload = json.dumps({"index": index, "revision": batch.revision, "batch_digest": result.digest,
                              "previous": previous}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        previous = hashlib.sha256(DOMAIN + payload).hexdigest()
        seen.add(result.digest)
        digests.append(result.digest)
        previous_revision = batch.revision
    if expected_digest is not None and previous != expected_digest:
        return ChainResult("CHAIN_DIGEST_MISMATCH")
    return ChainResult("CHAIN_FIXTURE_UNAUTHENTICATED", previous, tuple(digests))

def safe_to_promote(*args, **kwargs):
    return False
