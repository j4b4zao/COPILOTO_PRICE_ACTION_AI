"""F3-INT-36: in-memory anchored-copy assessment, not authentication or durability.

An Anchor is a *caller supplied assumption*. Nothing here authenticates the
caller, prevents rollback of the anchor itself, or elects an authoritative writer.
"""
from dataclasses import dataclass
from tools.f3_int34_persistence_simulator import replay


@dataclass(frozen=True)
class Anchor:
    sequence: int
    checksum: str


@dataclass(frozen=True)
class Assessment:
    status: str
    matched: bool
    authoritative: bool = False
    closure_authorized: bool = False


def assess_copy(records, anchor):
    records = tuple(records)
    replay(records)
    if not isinstance(anchor, Anchor) or type(anchor.sequence) is not int or anchor.sequence < 0 or not isinstance(anchor.checksum, str):
        raise ValueError('INVALID_ANCHOR')
    if anchor.sequence == 0:
        if anchor.checksum != 'GENESIS':
            return Assessment('ANCHOR_CONFLICT', False)
        return Assessment('UNANCHORED_SUFFIX', True)
    if len(records) < anchor.sequence:
        return Assessment('ROLLBACK_OR_INCOMPLETE', False)
    if records[anchor.sequence - 1].checksum != anchor.checksum:
        return Assessment('ANCHOR_CONFLICT', False)
    if len(records) == anchor.sequence:
        return Assessment('MATCHES_ANCHOR', True)
    return Assessment('UNVERIFIED_SUFFIX', True)


def assess_pair(left, right, anchor):
    a = assess_copy(left, anchor)
    b = assess_copy(right, anchor)
    if not a.matched and not b.matched:
        return 'NO_ANCHORED_COPY', a, b
    if a.matched != b.matched:
        return 'SINGLE_ANCHORED_COPY_UNVERIFIED', a, b
    left, right = tuple(left), tuple(right)
    common = 0
    for x, y in zip(left, right):
        if x != y:
            break
        common += 1
    if common < min(len(left), len(right)):
        return 'DIVERGENT_AFTER_ANCHOR', a, b
    if len(left) != len(right):
        return 'PREFIX_AFTER_ANCHOR_UNCERTAIN', a, b
    return 'IDENTICAL_NOT_AUTHORITATIVE', a, b


def safe_to_promote(*_args):
    return False
