"""F3-INT-112 offline file inventory: comparison, not provenance attestation.

Expected inventory MUST be retained outside the examined tree and independently
verified. A matching digest cannot prove which executable ran on another host.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import os

LOCKS = ('orders_allowed','live_certified','flow_complete','f3_resolved',
         'native_prototype_authorized','strict_deadline_guaranteed',
         'authenticated_witness_verified')

@dataclass(frozen=True)
class InventoryFinding:
    status: str
    observed: tuple = ()
    mismatch: tuple = ()
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False

def inspect_tree(root, expected):
    """Read-only deterministic inventory. Reject links, unexpected and missing files.

    This is not a TOCTOU-safe read against a malicious concurrent writer.
    """
    if not isinstance(expected, dict) or not expected:
        return InventoryFinding('INVALID_EXPECTED_INVENTORY')
    for key, value in expected.items():
        if (not isinstance(key, str) or not key or '\\' in key or
            key.startswith('/') or any(x in ('', '.', '..') for x in key.split('/')) or
            not isinstance(value, str) or len(value) != 64 or
            any(c not in '0123456789abcdef' for c in value)):
            return InventoryFinding('INVALID_EXPECTED_INVENTORY')
    try:
        root = Path(root)
        if root.is_symlink() or not root.is_dir():
            return InventoryFinding('INVALID_ROOT')
        observed = {}
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                item = Path(directory) / name
                if item.is_symlink():
                    return InventoryFinding('SYMLINK_REJECTED')
            for name in files:
                item = Path(directory) / name
                relative = item.relative_to(root).as_posix()
                h = hashlib.sha256()
                with item.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(block)
                observed[relative] = h.hexdigest()
        mismatch = tuple(sorted(k for k in set(expected) | set(observed)
                                if expected.get(k) != observed.get(k)))
        return InventoryFinding('MATCH_UNAUTHENTICATED' if not mismatch else 'INVENTORY_MISMATCH',
                                tuple(sorted(observed.items())), mismatch)
    except (OSError, ValueError):
        return InventoryFinding('INVENTORY_UNAVAILABLE')

def safe_to_promote(*args, **kwargs):
    return False
