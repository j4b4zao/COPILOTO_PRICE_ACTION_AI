"""F3-INT-115 offline inquiry policy; never retry or authorize operations.

Reuses the existing SQLite reconciliation. Pins are caller-retained evidence,
not authenticated custody. Local observations do not prove physical durability.
"""
from dataclasses import dataclass
from tools.f3_int110_offline_reconciliation import reconcile_consumption
from tools.f3_int109_offline_consumption_store import StoreResult


@dataclass(frozen=True)
class RecoveryObservation(StoreResult):
    retry_allowed: bool = False
    ack_state: str = 'UNKNOWN'


def observe_recovery(path, *, ack_state='UNKNOWN', **pins):
    if ack_state not in ('RECEIVED', 'LOST', 'UNKNOWN'):
        return RecoveryObservation('INVALID_ACK')
    result = reconcile_consumption(path, **pins)
    return RecoveryObservation(result.status, digest=result.digest,
                               state_digest=result.state_digest, ack_state=ack_state)


def safe_to_promote(*args, **kwargs):
    return False
