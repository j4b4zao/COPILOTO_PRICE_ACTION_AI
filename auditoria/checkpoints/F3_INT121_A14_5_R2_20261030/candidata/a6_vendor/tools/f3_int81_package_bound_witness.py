"""Bind a replayed crash witness to a verified offline package and caller pin."""
from dataclasses import dataclass
from io import BytesIO
import hashlib
import re
import zipfile
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int61_portable_package_simulator import portable_name
from a6_vendor.tools.f3_int70_crash_witness_codec import decode_witness,encode_witness
from a6_vendor.tools.f3_int73_package_lineage_simulator import PackageRecord
from a6_vendor.tools.f3_int78_verified_envelope import EnvelopePolicy,verify_envelope


@dataclass(frozen=True)
class BoundWitnessResult(ConcurrentResult):
    package_stage: int = 0
    package_sha256: str = ''
    path: str = ''
    payload_sha256: str = ''
    canonical_sha256: str = ''
    payload: bytes = b''


def assess_package_witness(record,path,canonical_pin,*,policy=EnvelopePolicy()):
    if type(record) is not PackageRecord:
        return BoundWitnessResult('INVALID_PACKAGE_WITNESS_RECORD')
    if type(path) is not str or len(path)>512 or not portable_name(path) or not path.endswith('.json'):
        return BoundWitnessResult('INVALID_WITNESS_PATH')
    if type(canonical_pin) is not str or not re.fullmatch('[0-9a-f]{64}',canonical_pin):
        return BoundWitnessResult('INVALID_CANONICAL_PIN')
    envelope=verify_envelope(record.blob,record.sha256,record.stage,policy=policy)
    if envelope.status!='VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED':
        return BoundWitnessResult('PACKAGE_WITNESS_'+envelope.status)
    with zipfile.ZipFile(BytesIO(record.blob)) as archive:
        if path not in archive.namelist(): return BoundWitnessResult('MISSING_PACKAGE_WITNESS')
        payload=archive.read(path)
    try:
        canonical=encode_witness(decode_witness(payload))
    except ValueError:
        return BoundWitnessResult('PACKAGE_WITNESS_REPLAY_REJECTED')
    digest=hashlib.sha256(canonical).hexdigest()
    if digest!=canonical_pin: return BoundWitnessResult('PACKAGE_WITNESS_PIN_MISMATCH')
    return BoundWitnessResult('PACKAGE_BOUND_WITNESS_FIXTURE_UNAUTHENTICATED',1,
                              package_stage=record.stage,package_sha256=record.sha256,path=path,
                              payload_sha256=hashlib.sha256(payload).hexdigest(),canonical_sha256=digest,payload=payload)


def safe_to_promote(*args,**kwargs): return False
