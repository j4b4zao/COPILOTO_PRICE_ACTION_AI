"""Policy-bound prepare/commit imports over caller-controlled offline snapshots."""
from dataclasses import dataclass
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int72_atomic_witness_batch_simulator import Registry
from a6_vendor.tools.f3_int78_verified_envelope import EnvelopePolicy
from a6_vendor.tools.f3_int82_atomic_package_witness_batch import assess_package_batch
from a6_vendor.tools.f3_int83_concurrent_import_simulator import MAX_VERSION,valid_registry,valid_requests


@dataclass(frozen=True)
class PolicySnapshot:
    version: int = 0
    registry: Registry = Registry()
    policy: EnvelopePolicy = EnvelopePolicy()


@dataclass(frozen=True)
class PolicyProposal:
    base: PolicySnapshot
    requests: tuple
    candidate: Registry


@dataclass(frozen=True)
class PolicyImportResult(ConcurrentResult):
    snapshot: PolicySnapshot = PolicySnapshot()
    proposal: object = None


def valid_policy_snapshot(value):
    return (type(value) is PolicySnapshot and type(value.version) is int and 0<=value.version<=MAX_VERSION
            and valid_registry(value.registry) and type(value.policy) is EnvelopePolicy
            and type(value.policy.max_files) is int and 1<=value.policy.max_files<=2048
            and type(value.policy.max_bytes) is int and 1<=value.policy.max_bytes<=67108864)


def prepare_policy_import(snapshot,requests):
    def reject(status): return PolicyImportResult(status,snapshot=snapshot)
    if not valid_policy_snapshot(snapshot): return reject('INVALID_POLICY_IMPORT_SNAPSHOT')
    if not valid_requests(requests): return reject('INVALID_IMPORT_REQUESTS')
    if snapshot.version==MAX_VERSION: return reject('IMPORT_VERSION_EXHAUSTED')
    checked=assess_package_batch(snapshot.registry,requests,policy=snapshot.policy)
    if checked.status!='ATOMIC_PACKAGE_WITNESS_BATCH_FIXTURE_UNAUTHENTICATED': return reject(checked.status)
    return PolicyImportResult('POLICY_IMPORT_PROPOSAL_FIXTURE_UNAUTHENTICATED',snapshot=snapshot,
                              proposal=PolicyProposal(snapshot,requests,checked.registry))


def commit_policy_import(snapshot,proposal):
    def reject(status): return PolicyImportResult(status,snapshot=snapshot)
    if not valid_policy_snapshot(snapshot): return reject('INVALID_POLICY_IMPORT_SNAPSHOT')
    if (type(proposal) is not PolicyProposal or not valid_policy_snapshot(proposal.base)
            or not valid_registry(proposal.candidate) or not valid_requests(proposal.requests)):
        return reject('INVALID_POLICY_IMPORT_PROPOSAL')
    if snapshot.version==MAX_VERSION: return reject('IMPORT_VERSION_EXHAUSTED')
    if snapshot!=proposal.base: return reject('STALE_POLICY_OR_IMPORT_SNAPSHOT')
    recomputed=prepare_policy_import(snapshot,proposal.requests)
    if recomputed.proposal is None: return reject(recomputed.status)
    if recomputed.proposal!=proposal: return reject('FORGED_POLICY_IMPORT_CANDIDATE')
    return PolicyImportResult('POLICY_IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED',
                              snapshot=PolicySnapshot(snapshot.version+1,proposal.candidate,snapshot.policy))


def safe_to_promote(*args,**kwargs): return False
