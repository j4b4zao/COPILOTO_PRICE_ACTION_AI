"""Typed atomic registry of replayed evidence references and finite observables.

Not the consumed-witness registry. IDs describe caller-controlled finite fixture
observations, not authenticity or general semantic equivalence. Reset permits
replay again. No operational permission follows from registration.
"""
from dataclasses import asdict,dataclass
import hashlib
import json
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid
from tools.f3_int88_import_divergence_witness import classify_import_ends
from tools.f3_int89_import_witness_codec import encode_import_witness,run_digest
from tools.f3_int90_import_witness_bundle import MAX_BUNDLE_BYTES,decode_import_bundle

NAMESPACE='IMPORT_DIVERGENCE_V1'


@dataclass(frozen=True)
class EvidenceRegistry:
    reference_ids: tuple = ()
    observable_ids: tuple = ()
    namespace: str = NAMESPACE


@dataclass(frozen=True)
class BundleRecord:
    blob: bytes
    sha256: str


@dataclass(frozen=True)
class EvidenceReceipt:
    reference_id: str
    observable_id: str
    classification: str


@dataclass(frozen=True)
class EvidenceResult(ConcurrentResult):
    registry: EvidenceRegistry = EvidenceRegistry()
    receipts: tuple = ()


def describe_bundle(blob,digest):
    witness=decode_import_bundle(blob,digest)
    canonical=encode_import_witness(witness)
    reference_id=hashlib.sha256(NAMESPACE.encode()+b'\0REFERENCE\0'+canonical).hexdigest()
    observations=dict(initial=asdict(witness.initial),
                      batches=[[r.canonical_pin for r in batch] for batch in witness.batches],
                      unordered_trace_ids=sorted((run_digest(witness.left),run_digest(witness.right))))
    body=json.dumps(observations,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    observable_id=hashlib.sha256(NAMESPACE.encode()+b'\0OBSERVATIONS\0'+body).hexdigest()
    return EvidenceReceipt(reference_id,observable_id,classify_import_ends(witness.left.snapshots[-1],witness.right.snapshots[-1]))


def valid_evidence_registry(value):
    return (type(value) is EvidenceRegistry and type(value.namespace) is str and value.namespace==NAMESPACE
            and type(value.reference_ids) is tuple and type(value.observable_ids) is tuple
            and len(value.reference_ids)==len(value.observable_ids)<=256
            and all(digest_valid(d) for d in value.reference_ids+value.observable_ids)
            and len(set(value.reference_ids))==len(value.reference_ids)
            and len(set(value.observable_ids))==len(value.observable_ids))


def register_evidence_batch(registry,records,*,max_total_bytes=67108864):
    def reject(status): return EvidenceResult(status,registry=registry)
    if type(max_total_bytes) is not int or not 1<=max_total_bytes<=67108864:
        return reject('INVALID_EVIDENCE_BYTE_BOUND')
    if not valid_evidence_registry(registry): return reject('INVALID_TYPED_EVIDENCE_REGISTRY')
    if (type(records) is not tuple or not 1<=len(records)<=8
            or any(type(r) is not BundleRecord or type(r.blob) is not bytes or not 1<=len(r.blob)<=MAX_BUNDLE_BYTES
                   or not digest_valid(r.sha256) for r in records)):
        return reject('INVALID_EVIDENCE_BATCH')
    if sum(len(r.blob) for r in records)>max_total_bytes: return reject('EVIDENCE_TOTAL_BYTE_LIMIT')
    if len(registry.reference_ids)+len(records)>256: return reject('EVIDENCE_REGISTRY_LIMIT')
    references=set(registry.reference_ids); observations=set(registry.observable_ids); receipts=[]
    for record in records:
        try: receipt=describe_bundle(record.blob,record.sha256)
        except ValueError: return reject('EVIDENCE_BUNDLE_REJECTED')
        if receipt.reference_id in references: return reject('EVIDENCE_REFERENCE_REPLAY')
        if receipt.observable_id in observations: return reject('EVIDENCE_OBSERVABLE_REPLAY')
        references.add(receipt.reference_id); observations.add(receipt.observable_id); receipts.append(receipt)
    updated=EvidenceRegistry(registry.reference_ids+tuple(r.reference_id for r in receipts),
                              registry.observable_ids+tuple(r.observable_id for r in receipts))
    return EvidenceResult('EVIDENCE_REGISTERED_FIXTURE_UNAUTHENTICATED',len(receipts),registry=updated,receipts=tuple(receipts))


def safe_to_promote(*args,**kwargs): return False
