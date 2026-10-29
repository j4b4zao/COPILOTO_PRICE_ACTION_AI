"""F3-INT-113: offline execution-inventory evidence comparison, never attestation.

The expected reference MUST be retained and trusted independently of this tree.
Neither local digest matches nor self-asserted provenance authenticate execution.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from .f3_int112_snapshot_inventory import inspect_tree, LOCKS

@dataclass(frozen=True)
class ExecutionComparison:
    status: str
    before_status: str = 'NOT_CHECKED'
    after_status: str = 'NOT_CHECKED'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False

def canonical_digest(inventory):
    """Deterministic digest, not an authenticity proof."""
    if not isinstance(inventory, dict) or not inventory:
        return None
    for name, digest in inventory.items():
        if (not isinstance(name, str) or not name or '\\' in name or
            name.startswith('/') or any(x in ('', '.', '..') for x in name.split('/')) or
            not isinstance(digest, str) or len(digest) != 64 or
            any(c not in '0123456789abcdef' for c in digest)):
            return None
    blob = json.dumps(inventory, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return hashlib.sha256(b'F3-INT-113-INVENTORY\0' + blob).hexdigest()

def compare_execution_snapshots(before_root, after_root, expected, retained_digest,
                                *, independent_reference=False, reference_revoked=False):
    """Compare two offline snapshots against a separately retained inventory.

    This does NOT establish actual Windows execution identity: snapshots are
    caller-supplied, and neither their capture time nor custody is attested.
    """
    if reference_revoked:
        return ExecutionComparison('REFERENCE_REVOKED')
    if independent_reference is not True:
        return ExecutionComparison('INDEPENDENCE_NOT_ESTABLISHED')
    computed = canonical_digest(expected)
    if computed is None or not isinstance(retained_digest, str) or len(retained_digest) != 64 or any(c not in '0123456789abcdef' for c in retained_digest):
        return ExecutionComparison('INVALID_REFERENCE')
    if computed != retained_digest:
        return ExecutionComparison('REFERENCE_DIVERGENCE')
    before = inspect_tree(before_root, expected)
    after = inspect_tree(after_root, expected)
    if before.status != 'MATCH_UNAUTHENTICATED' or after.status != 'MATCH_UNAUTHENTICATED':
        return ExecutionComparison('SNAPSHOT_UNRESOLVED', before.status, after.status)
    return ExecutionComparison('BOTH_MATCH_UNAUTHENTICATED', before.status, after.status)

def safe_to_promote(*args, **kwargs):
    return False
