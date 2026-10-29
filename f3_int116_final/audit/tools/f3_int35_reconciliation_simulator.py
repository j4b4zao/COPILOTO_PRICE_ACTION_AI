"""F3-INT-35: read-only reconciliation of IN-MEMORY simulated journal copies.

No consensus, durable anchor, disk persistence, or authorization is implied.
A validated snapshot can never grant write authority or certify closure.
"""
from dataclasses import dataclass
from tools.f3_int34_persistence_simulator import replay


@dataclass(frozen=True)
class Reconciliation:
    status: str
    common_length: int
    left_length: int
    right_length: int
    authoritative: bool = False
    closure_authorized: bool = False


def reconcile(left, right, trusted_anchor=None):
    """Compare two independently validated copies against an optional trusted anchor.

    The anchor must be a (sequence, checksum) taken from a separately trusted
    authority. An unanchored or equal pair is NEVER authoritative. Prefix
    agreement does not establish whether a longer copy was committed.
    """
    left, right = tuple(left), tuple(right)
    replay(left)
    replay(right)
    common = 0
    for l, r in zip(left, right):
        if l != r:
            break
        common += 1
    if trusted_anchor is not None:
        if (not isinstance(trusted_anchor, tuple) or len(trusted_anchor) != 2 or
                type(trusted_anchor[0]) is not int or trusted_anchor[0] < 0 or
                not isinstance(trusted_anchor[1], str)):
            raise ValueError('INVALID_ANCHOR')
        seq, digest = trusted_anchor
        def matches(records):
            return (seq == 0 and digest == 'GENESIS') or (len(records) >= seq > 0 and records[seq-1].checksum == digest)
        if not matches(left) and not matches(right):
            return Reconciliation('ANCHOR_NOT_FOUND', common, len(left), len(right))
        if matches(left) != matches(right):
            return Reconciliation('ANCHOR_MISSING_FROM_COPY', common, len(left), len(right))
    if common < min(len(left), len(right)):
        status = 'DIVERGENT'
    elif len(left) == len(right):
        status = 'IDENTICAL_UNVERIFIED'
    else:
        status = 'PREFIX_UNCERTAIN'
    return Reconciliation(status, common, len(left), len(right))


def safe_to_promote(_reconciliation):
    return False
