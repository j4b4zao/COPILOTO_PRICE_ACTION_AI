"""F3-INT-41: in-memory fencing/worker handoff fixture. No real authority."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Transfer:
    kind: str
    worker: str
    generation: int
    parent: int
    token: str

@dataclass(frozen=True)
class TransferResult:
    status: str
    fixture_consistent: bool = False
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False

def assess_transfers(events, expected_worker=None, expected_generation=None):
    try: events = tuple(events)
    except TypeError: return TransferResult('INVALID_EVENTS')
    if not events: return TransferResult('MISSING_TRANSFER_HISTORY')
    if any(not isinstance(e, Transfer) or e.kind not in ('ACQUIRE','RELEASE','WRITE')
           or not isinstance(e.worker,str) or not e.worker or type(e.generation) is not int
           or e.generation < 1 or type(e.parent) is not int or e.parent < 0
           or not isinstance(e.token,str) or not e.token for e in events):
        return TransferResult('INVALID_EVENTS')
    active = None; generation = 0; released = False; tokens=set()
    for e in events:
        if e.kind == 'ACQUIRE':
            if e.token in tokens: return TransferResult('REPLAYED_TRANSFER_TOKEN')
            if e.parent != generation: return TransferResult('CAUSAL_PARENT_MISMATCH')
            if active is not None and not released: return TransferResult('UNFENCED_HANDOFF')
            if e.generation != generation + 1: return TransferResult('INVALID_GENERATION_ADVANCE')
            active = e.worker; generation=e.generation; released=False; tokens.add(e.token)
        elif e.kind == 'RELEASE':
            if active != e.worker or e.generation != generation or released:
                return TransferResult('STALE_OR_DUPLICATE_RELEASE')
            if e.parent != generation: return TransferResult('CAUSAL_PARENT_MISMATCH')
            released=True
        else:
            if e.parent != generation: return TransferResult('CAUSAL_PARENT_MISMATCH')
            if e.generation != generation or e.worker != active or released:
                return TransferResult('FENCED_OR_STALE_WRITE')
    if active is None or released: return TransferResult('NO_ACTIVE_WRITER')
    if expected_worker is not None and expected_worker != active: return TransferResult('WRITER_MISMATCH')
    if expected_generation is not None and expected_generation != generation: return TransferResult('GENERATION_MISMATCH')
    return TransferResult('FIXTURE_HANDOFF_CONSISTENT_NOT_AUTHENTICATED', True)

def safe_to_promote(*_args,**_kwargs): return False
