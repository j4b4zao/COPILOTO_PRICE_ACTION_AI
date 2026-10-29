"""Compare references and finite observable identities of replayed bundle fixtures.

Equality is restricted to the recorded model observations. It does not imply
general program equivalence, authenticity, consensus or operational readiness.
"""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid
from tools.f3_int90_import_witness_bundle import MAX_BUNDLE_BYTES
from tools.f3_int91_evidence_registry import BundleRecord,describe_bundle


@dataclass(frozen=True)
class ObservationRelation(ConcurrentResult):
    same_reference: bool = False
    same_observations: bool = False


def compare_bundle_observations(left,right):
    if any(type(r) is not BundleRecord or type(r.blob) is not bytes or not 1<=len(r.blob)<=MAX_BUNDLE_BYTES
           or not digest_valid(r.sha256) for r in (left,right)):
        return ObservationRelation('INVALID_OBSERVATION_RELATION_INPUT')
    if len(left.blob)+len(right.blob)>67108864: return ObservationRelation('OBSERVATION_RELATION_BYTE_LIMIT')
    try:
        a=describe_bundle(left.blob,left.sha256); b=describe_bundle(right.blob,right.sha256)
    except ValueError:
        return ObservationRelation('OBSERVATION_RELATION_BUNDLE_REJECTED')
    reference=a.reference_id==b.reference_id; observed=a.observable_id==b.observable_id
    if reference and not observed or observed and a.classification!=b.classification:
        return ObservationRelation('INCONSISTENT_EVIDENCE_IDENTITIES')
    status=('SAME_EVIDENCE_REFERENCE_FIXTURE_UNAUTHENTICATED' if reference else
            'SAME_FINITE_OBSERVATIONS_FIXTURE_UNAUTHENTICATED' if observed else
            'DISTINCT_FINITE_OBSERVATIONS_FIXTURE_UNAUTHENTICATED')
    return ObservationRelation(status,2,same_reference=reference,same_observations=observed)


def safe_to_promote(*args,**kwargs): return False
