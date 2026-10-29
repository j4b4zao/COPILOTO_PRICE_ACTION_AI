"""Finite differential envelope checks; explicit capacity extensions are labeled."""
from dataclasses import dataclass
from io import BytesIO
import zipfile
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int62_strict_evidence_simulator import verify_strict_blob,strict_json
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int75_source_inventory_guard import verify_guarded_lineage
from tools.f3_int78_verified_envelope import EnvelopePolicy,verify_envelope


@dataclass(frozen=True)
class ContractResult(ConcurrentResult):
    observations: tuple = ()


def audit_envelope_contracts(records,*,policy=EnvelopePolicy()):
    if (type(policy) is not EnvelopePolicy or type(policy.max_files) is not int or not 1<=policy.max_files<=2048
            or type(policy.max_bytes) is not int or not 1<=policy.max_bytes<=67108864):
        return ContractResult('INVALID_CONTRACT_POLICY')
    if (type(records) is not tuple or not 1<=len(records)<=16
            or any(type(r) is not PackageRecord or type(r.stage) is not int or not 2<=r.stage<=9999
                   or type(r.blob) is not bytes for r in records)):
        return ContractResult('INVALID_CONTRACT_RECORDS')
    if sum(len(r.blob) for r in records)>33554432: return ContractResult('CONTRACT_BYTE_LIMIT')
    observations=[]; mismatch=False
    for record in records:
        old=verify_strict_blob(record.blob,record.sha256,record.stage)
        old_accepted=old.status=='STRICT_EVIDENCE_FIXTURE_UNAUTHENTICATED'
        old_status=old.status
        if old_accepted:
            with zipfile.ZipFile(BytesIO(record.blob)) as archive:
                state=strict_json(archive.read(f'CHECKPOINT_F3_INT{record.stage}.json'))
            if state['regression']['tests']<=state['new_tests']['tests']:
                return ContractResult('OUTSIDE_POSITIVE_ANCHOR_DOMAIN')
            guard=verify_guarded_lineage((record,),anchor_stage=record.stage-1,
                                         anchor_tests=state['regression']['tests']-state['new_tests']['tests'])
            old_accepted=guard.status=='DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED'
            old_status=guard.status
        new=verify_envelope(record.blob,record.sha256,record.stage,policy=policy)
        new_accepted=new.status=='VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED'
        classification='AGREE' if old_accepted==new_accepted else 'CONSERVATIVE_NEW_REJECTION'
        if new_accepted and not old_accepted:
            with zipfile.ZipFile(BytesIO(record.blob)) as archive: files=len(archive.infolist())
            if old.status=='ARCHIVE_LIMIT_EXCEEDED' and 512<files<=policy.max_files:
                classification='EXPLICIT_FILE_CAPACITY_EXTENSION'
            else:
                classification='UNEXPECTED_NEW_ACCEPTANCE'; mismatch=True
        observations.append((record.stage,old_status,new.status,classification))
    return ContractResult('ENVELOPE_CONTRACT_MISMATCH' if mismatch else 'ENVELOPE_CONTRACTS_FIXTURE_UNAUTHENTICATED',
                           len(observations),observations=tuple(observations))


def safe_to_promote(*args,**kwargs): return False
