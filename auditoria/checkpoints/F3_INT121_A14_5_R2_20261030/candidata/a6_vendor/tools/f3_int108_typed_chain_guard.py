"""Offline verification against caller-maintained expectations; no authentication.

The caller must retain the pin, revision floor and consumed digests independently
of the submitted chain. Rollback/replacement of that state defeats replay checks.
This pure function does not persist or atomically consume anything.
"""
from a6_vendor.tools.f3_int107_typed_batch_chain import ChainResult, build_typed_chain
from a6_vendor.tools.f3_int72_atomic_witness_batch_simulator import digest_valid


def verify_typed_chain(segments, *, context, purpose, run_id, batches,
                       expected_digest, minimum_revision, consumed_chain_digests,
                       base_registry=None):
    """Verify a complete pinned window whose revisions exceed a retained floor.

    minimum_revision is inclusive. Explicit empty consumption history is allowed
    for a first verification. On success the caller must retain the digest and
    advance its floor before another admission; concurrent admission is not solved.
    Existing chain validation and digest comparison are delegated to INT-107.
    """
    if not digest_valid(expected_digest):
        return ChainResult("INVALID_REQUIRED_CHAIN_PIN")
    if type(minimum_revision) is not int or not 0 <= minimum_revision <= 2147483647:
        return ChainResult("INVALID_MINIMUM_REVISION")
    if (type(consumed_chain_digests) is not frozenset
            or len(consumed_chain_digests) > 4096
            or any(not digest_valid(d) for d in consumed_chain_digests)):
        return ChainResult("INVALID_CONSUMED_CHAIN_DIGESTS")
    result = build_typed_chain(
        segments, context=context, purpose=purpose, run_id=run_id,
        batches=batches, base_registry=base_registry,
        expected_digest=expected_digest)
    if result.status != "CHAIN_FIXTURE_UNAUTHENTICATED":
        return result
    # INT-107 already enforces a nonempty tuple and strictly increasing revisions.
    if batches[0].revision < minimum_revision:
        return ChainResult("STALE_CHAIN_REVISION")
    if result.digest in consumed_chain_digests:
        return ChainResult("CHAIN_ALREADY_CONSUMED")
    return result


def safe_to_promote(*args, **kwargs):
    return False
