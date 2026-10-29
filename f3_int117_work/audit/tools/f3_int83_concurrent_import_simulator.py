"""Sequential prepare/commit model of concurrent offline witness imports.

Registry snapshots, versions and package pins are caller-controlled fixtures.
Revalidation and stale detection do not implement native fencing or persistence.
"""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int72_atomic_witness_batch_simulator import Registry,digest_valid
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int82_atomic_package_witness_batch import PackageWitnessRequest,assess_package_batch

MAX_VERSION=2**63-1


@dataclass(frozen=True)
class RegistrySnapshot:
    version: int = 0
    registry: Registry = Registry()


@dataclass(frozen=True)
class ImportProposal:
    base: RegistrySnapshot
    requests: tuple
    candidate: Registry


@dataclass(frozen=True)
class ImportResult(ConcurrentResult):
    snapshot: RegistrySnapshot = RegistrySnapshot()
    proposal: object = None


def valid_registry(value):
    return (type(value) is Registry and type(value.digests) is tuple and len(value.digests)<=256
            and all(digest_valid(d) for d in value.digests) and len(set(value.digests))==len(value.digests))


def valid_snapshot(value):
    return (type(value) is RegistrySnapshot and type(value.version) is int and 0<=value.version<=MAX_VERSION
            and valid_registry(value.registry))


def valid_requests(requests):
    return (type(requests) is tuple and 1<=len(requests)<=16
            and all(type(r) is PackageWitnessRequest and type(r.record) is PackageRecord
                    and type(r.record.stage) is int and 1<=r.record.stage<=9999
                    and type(r.record.blob) is bytes and digest_valid(r.record.sha256)
                    and type(r.path) is str and len(r.path)<=512 and digest_valid(r.canonical_pin) for r in requests)
            and sum(len(r.record.blob) for r in requests)<=33554432)


def prepare_import(snapshot,requests):
    def reject(status): return ImportResult(status,snapshot=snapshot)
    if not valid_snapshot(snapshot): return reject('INVALID_IMPORT_SNAPSHOT')
    if not valid_requests(requests): return reject('INVALID_IMPORT_REQUESTS')
    if snapshot.version==MAX_VERSION: return reject('IMPORT_VERSION_EXHAUSTED')
    assessed=assess_package_batch(snapshot.registry,requests)
    if assessed.status!='ATOMIC_PACKAGE_WITNESS_BATCH_FIXTURE_UNAUTHENTICATED': return reject(assessed.status)
    return ImportResult('IMPORT_PROPOSAL_FIXTURE_UNAUTHENTICATED',snapshot=snapshot,
                        proposal=ImportProposal(snapshot,requests,assessed.registry))


def commit_import(snapshot,proposal):
    def reject(status): return ImportResult(status,snapshot=snapshot)
    if not valid_snapshot(snapshot): return reject('INVALID_IMPORT_SNAPSHOT')
    if (type(proposal) is not ImportProposal or not valid_snapshot(proposal.base)
            or not valid_registry(proposal.candidate) or not valid_requests(proposal.requests)):
        return reject('INVALID_IMPORT_PROPOSAL')
    if snapshot.version==MAX_VERSION: return reject('IMPORT_VERSION_EXHAUSTED')
    if proposal.base!=snapshot: return reject('STALE_IMPORT_SNAPSHOT')
    rechecked=prepare_import(snapshot,proposal.requests)
    if rechecked.proposal is None: return reject(rechecked.status)
    if rechecked.proposal!=proposal: return reject('FORGED_IMPORT_CANDIDATE')
    return ImportResult('IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED',
                        snapshot=RegistrySnapshot(snapshot.version+1,proposal.candidate))


def safe_to_promote(*args,**kwargs): return False
