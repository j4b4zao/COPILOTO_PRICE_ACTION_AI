"""Atomic offline package-bound witness ingestion over a caller-held registry."""
from dataclasses import dataclass
from tools.f3_int72_atomic_witness_batch_simulator import Registry,EncodedRecord,BatchResult,digest_valid,assess_batch
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int78_verified_envelope import EnvelopePolicy
from tools.f3_int81_package_bound_witness import assess_package_witness


@dataclass(frozen=True)
class PackageWitnessRequest:
    record: PackageRecord
    path: str
    canonical_pin: str


@dataclass(frozen=True)
class PackageBatchResult(BatchResult):
    bindings: tuple = ()


def assess_package_batch(registry,requests,*,policy=EnvelopePolicy(),max_package_bytes=33554432):
    def reject(status): return PackageBatchResult(status,registry=registry)
    if type(max_package_bytes) is not int or not 1<=max_package_bytes<=33554432:
        return reject('INVALID_PACKAGE_BATCH_BOUND')
    if (type(registry) is not Registry or type(registry.digests) is not tuple or len(registry.digests)>256
            or any(not digest_valid(d) for d in registry.digests) or len(set(registry.digests))!=len(registry.digests)):
        return reject('INVALID_WITNESS_REGISTRY')
    if (type(requests) is not tuple or not 1<=len(requests)<=16
            or any(type(r) is not PackageWitnessRequest or type(r.record) is not PackageRecord
                   or type(r.record.blob) is not bytes for r in requests)):
        return reject('INVALID_PACKAGE_WITNESS_BATCH')
    if sum(len(r.record.blob) for r in requests)>max_package_bytes:
        return reject('PACKAGE_BATCH_BYTE_LIMIT')
    records=[]; bindings=[]
    for request in requests:
        evidence=assess_package_witness(request.record,request.path,request.canonical_pin,policy=policy)
        if evidence.status!='PACKAGE_BOUND_WITNESS_FIXTURE_UNAUTHENTICATED':
            return reject('BATCH_'+evidence.status)
        records.append(EncodedRecord(evidence.payload,evidence.payload_sha256))
        bindings.append((evidence.package_stage,evidence.package_sha256,evidence.path,evidence.canonical_sha256))
    result=assess_batch(registry,tuple(records))
    if result.status!='BATCH_WITNESS_FIXTURE_UNAUTHENTICATED': return reject(result.status)
    return PackageBatchResult('ATOMIC_PACKAGE_WITNESS_BATCH_FIXTURE_UNAUTHENTICATED',result.checked,
                               registry=result.registry,bindings=tuple(bindings))


def safe_to_promote(*args,**kwargs): return False
