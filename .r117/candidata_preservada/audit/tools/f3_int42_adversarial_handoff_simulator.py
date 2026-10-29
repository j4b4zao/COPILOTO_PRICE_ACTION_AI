"""F3-INT-42: offline comparison of forged and divergent in-memory handoff histories.
No source authentication, consensus, cryptographic signatures, or real fencing.
"""
from dataclasses import dataclass
from tools.f3_int41_worker_handoff_simulator import assess_transfers

@dataclass(frozen=True)
class CrossViewResult:
    status: str
    common_events: int = 0
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False

def compare_views(left, right, pinned=None):
    try:
        left, right = tuple(left), tuple(right)
    except TypeError:
        return CrossViewResult('INVALID_VIEW')
    l, r = assess_transfers(left), assess_transfers(right)
    if not l.fixture_consistent or not r.fixture_consistent:
        return CrossViewResult('INVALID_LOCAL_VIEW')
    common = 0
    for a,b in zip(left,right):
        if a != b: break
        common += 1
    if pinned is None:
        return CrossViewResult('MISSING_INDEPENDENT_REFERENCE',common)
    if not isinstance(pinned, tuple) or len(pinned)!=2 or type(pinned[0]) is not int or pinned[0]<1:
        return CrossViewResult('INVALID_PIN',common)
    seq, event = pinned
    if seq>len(left) or seq>len(right):
        return CrossViewResult('PIN_UNAVAILABLE_IN_VIEW',common)
    if left[seq-1]!=event or right[seq-1]!=event:
        return CrossViewResult('PIN_CONFLICT',common)
    if left!=right:
        if common == min(len(left),len(right)):
            return CrossViewResult('PREFIX_UNCERTAIN',common)
        return CrossViewResult('DIVERGENT_VALID_LOCAL_HISTORIES',common)
    return CrossViewResult('IDENTICAL_PINNED_FIXTURE_NOT_AUTHENTICATED',common)

def safe_to_promote(*_args, **_kwargs): return False
