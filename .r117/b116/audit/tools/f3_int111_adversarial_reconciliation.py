"""F3-INT-111: audit-only adversarial assessment; no operational authority.

Pins are caller assertions, not authenticated provenance. An observer cannot
establish whether a pin was retained independently merely from its digest.
"""
from dataclasses import dataclass
from tools.f3_int110_offline_reconciliation import reconcile_consumption
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

@dataclass(frozen=True)
class AdversarialFinding:
    status: str
    observed_status: str = ''
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False

def assess_reconciliation(path, *, before_state_digest, after_state_digest,
                          expected_chain_digest, context, purpose, run_id,
                          independent_pins_attested=False,
                          stable_snapshot_attested=False):
    """Conservative evidence gate, never certifies independence or durability.

    Boolean attestations are UNTRUSTED caller claims. Even both True cannot
    prove provenance or stable state. Positive observations remain advisory.
    """
    if type(independent_pins_attested) is not bool or type(stable_snapshot_attested) is not bool:
        return AdversarialFinding('INVALID_AUDIT_CLAIM')
    if not all(digest_valid(x) for x in
               (before_state_digest, after_state_digest, expected_chain_digest)):
        return AdversarialFinding('INVALID_AUDIT_PIN')
    if not independent_pins_attested:
        return AdversarialFinding('PIN_INDEPENDENCE_UNPROVEN')
    if not stable_snapshot_attested:
        return AdversarialFinding('SNAPSHOT_STABILITY_UNPROVEN')
    observed = reconcile_consumption(path, before_state_digest=before_state_digest,
        after_state_digest=after_state_digest, expected_chain_digest=expected_chain_digest,
        context=context, purpose=purpose, run_id=run_id)
    if observed.status in ('COMMITTED_OBSERVED_UNAUTHENTICATED',
                           'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED'):
        return AdversarialFinding('OBSERVATION_ONLY_UNAUTHENTICATED', observed.status)
    return AdversarialFinding('FAIL_CLOSED', observed.status)

def safe_to_promote(*args, **kwargs):
    return False
