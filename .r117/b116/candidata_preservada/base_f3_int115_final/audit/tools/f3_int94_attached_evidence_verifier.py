"""Verify package -> attached bundle -> catalog -> witness -> recorded observations.

All expected pins are supplied by the caller. Internal consistency is not
independent attestation, certification or operational permission.
"""
from dataclasses import dataclass
from io import BytesIO
import hashlib
import zipfile
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int61_portable_package_simulator import portable_name
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int78_verified_envelope import EnvelopePolicy,verify_envelope
from tools.f3_int90_import_witness_bundle import MAX_BUNDLE_BYTES
from tools.f3_int91_evidence_registry import describe_bundle


@dataclass(frozen=True)
class AttachedEvidenceResult(ConcurrentResult):
    package_stage: int = 0
    package_sha256: str = ''
    path: str = ''
    bundle_sha256: str = ''
    reference_id: str = ''
    observable_id: str = ''
    classification: str = ''


def assess_attached_evidence(record,path,bundle_pin,observable_pin,*,policy=EnvelopePolicy(1024)):
    if type(record) is not PackageRecord: return AttachedEvidenceResult('INVALID_ATTACHED_EVIDENCE_RECORD')
    if (type(path) is not str or len(path)>512 or not portable_name(path) or not path.endswith('.witnessbundle')):
        return AttachedEvidenceResult('INVALID_ATTACHED_EVIDENCE_PATH')
    if not digest_valid(bundle_pin) or not digest_valid(observable_pin): return AttachedEvidenceResult('INVALID_ATTACHED_EVIDENCE_PIN')
    verified=verify_envelope(record.blob,record.sha256,record.stage,policy=policy)
    if verified.status!='VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED':
        return AttachedEvidenceResult('ATTACHED_'+verified.status)
    with zipfile.ZipFile(BytesIO(record.blob)) as archive:
        if path not in archive.namelist(): return AttachedEvidenceResult('MISSING_ATTACHED_EVIDENCE')
        if archive.getinfo(path).file_size>MAX_BUNDLE_BYTES: return AttachedEvidenceResult('ATTACHED_BUNDLE_BYTE_LIMIT')
        blob=archive.read(path)
    if hashlib.sha256(blob).hexdigest()!=bundle_pin: return AttachedEvidenceResult('ATTACHED_BUNDLE_PIN_MISMATCH')
    try: receipt=describe_bundle(blob,bundle_pin)
    except ValueError: return AttachedEvidenceResult('ATTACHED_BUNDLE_REPLAY_REJECTED')
    if receipt.observable_id!=observable_pin: return AttachedEvidenceResult('ATTACHED_OBSERVABLE_PIN_MISMATCH')
    return AttachedEvidenceResult('ATTACHED_EVIDENCE_REPLAYED_FIXTURE_UNAUTHENTICATED',1,
                                   package_stage=record.stage,package_sha256=record.sha256,path=path,
                                   bundle_sha256=bundle_pin,reference_id=receipt.reference_id,
                                   observable_id=receipt.observable_id,classification=receipt.classification)


def safe_to_promote(*args,**kwargs): return False
