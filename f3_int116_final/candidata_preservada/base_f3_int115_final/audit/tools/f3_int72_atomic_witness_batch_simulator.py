"""Atomic offline witness ingestion with caller-held canonical replay registry.

The registry is a fixture, not authenticated or durable. Resetting it defeats
cross-batch replay detection; no operational permission can result from a batch.
"""
from dataclasses import dataclass
import hashlib
import re
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int70_crash_witness_codec import MAX_BYTES, decode_witness, encode_witness


@dataclass(frozen=True)
class Registry:
    digests: tuple = ()


@dataclass(frozen=True)
class EncodedRecord:
    payload: bytes
    sha256: str


@dataclass(frozen=True)
class BatchResult(ConcurrentResult):
    registry: Registry = Registry()


def digest_valid(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def assess_batch(registry,records,*,max_records=16,max_total_bytes=1048576,max_memory=256):
    def reject(status): return BatchResult(status,registry=registry)
    if (type(max_records) is not int or not 1<=max_records<=16
            or type(max_total_bytes) is not int or not 1<=max_total_bytes<=1048576
            or type(max_memory) is not int or not 1<=max_memory<=256):
        return reject('INVALID_BATCH_BOUND')
    if (type(registry) is not Registry or type(registry.digests) is not tuple
            or len(registry.digests)>max_memory or any(not digest_valid(d) for d in registry.digests)
            or len(set(registry.digests))!=len(registry.digests)):
        return reject('INVALID_WITNESS_REGISTRY')
    if type(records) is not tuple or not 1<=len(records)<=max_records:
        return reject('INVALID_WITNESS_BATCH')
    if any(type(r) is not EncodedRecord or type(r.payload) is not bytes
           or not 1<=len(r.payload)<=MAX_BYTES or not digest_valid(r.sha256) for r in records):
        return reject('INVALID_ENCODED_RECORD')
    if sum(len(r.payload) for r in records)>max_total_bytes:
        return reject('BATCH_BYTE_LIMIT_EXCEEDED')
    if len(registry.digests)+len(records)>max_memory:
        return reject('REGISTRY_LIMIT_EXCEEDED')
    seen=set(registry.digests); added=[]
    for record in records:
        if hashlib.sha256(record.payload).hexdigest()!=record.sha256:
            return reject('RECORD_DIGEST_MISMATCH')
        try:
            canonical=encode_witness(decode_witness(record.payload))
        except ValueError:
            return reject('BATCH_WITNESS_REPLAY_REJECTED')
        digest=hashlib.sha256(canonical).hexdigest()
        if digest in seen: return reject('REPLAYED_CANONICAL_WITNESS')
        seen.add(digest); added.append(digest)
    return BatchResult('BATCH_WITNESS_FIXTURE_UNAUTHENTICATED',len(added),
                       registry=Registry(registry.digests+tuple(added)))


def safe_to_promote(*args,**kwargs):
    return False
