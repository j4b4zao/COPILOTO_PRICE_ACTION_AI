"""Offline package lineage with exact declared replacements, never authorization.

Reasons and hashes are caller-controlled annotations. This verifies consistency,
not permission to change code or authenticity of its origin. Source removal is
rejected; additions need no replacement declaration. Legacy verifier is intact.
"""
from dataclasses import dataclass
from io import BytesIO
import hashlib
import re
import zipfile
from a6_vendor.tools.f3_int60_package_integrity_simulator import safe_name
from a6_vendor.tools.f3_int62_strict_evidence_simulator import verify_strict_blob, strict_json
from a6_vendor.tools.f3_int73_package_lineage_simulator import PackageRecord, LineageResult


@dataclass(frozen=True)
class SourceDelta:
    stage: int
    path: str
    before: str
    after: str
    reason: str


@dataclass(frozen=True)
class DeltaLineageResult(LineageResult):
    applied: tuple = ()


def source_path(path):
    return (type(path) is str and len(path)<=512 and safe_name(path)
            and path.startswith(('tests/','tools/')) and path.endswith('.py'))


def verify_declared_lineage(records,deltas=(),*,anchor_stage=52,anchor_tests=526,max_total_bytes=33554432):
    def reject(status,checked=0): return DeltaLineageResult(status,checked)
    if (type(anchor_stage) is not int or not 1<=anchor_stage<=9999
            or type(anchor_tests) is not int or anchor_tests<1
            or type(max_total_bytes) is not int or not 1<=max_total_bytes<=33554432):
        return reject('INVALID_LINEAGE_BOUND')
    if (type(records) is not tuple or not 1<=len(records)<=32
            or any(type(r) is not PackageRecord or type(r.stage) is not int or type(r.blob) is not bytes for r in records)):
        return reject('INVALID_LINEAGE_RECORDS')
    if sum(len(r.blob) for r in records)>max_total_bytes: return reject('LINEAGE_BYTE_LIMIT_EXCEEDED')
    if type(deltas) is not tuple or len(deltas)>256: return reject('INVALID_SOURCE_DELTAS')
    declarations={}
    for d in deltas:
        if (type(d) is not SourceDelta or type(d.stage) is not int or not 1<=d.stage<=9999
                or not source_path(d.path) or type(d.reason) is not str or not d.reason.strip() or len(d.reason)>512
                or any(type(h) is not str or not re.fullmatch('[0-9a-f]{64}',h) for h in (d.before,d.after))
                or d.before==d.after):
            return reject('INVALID_SOURCE_DELTAS')
        key=(d.stage,d.path)
        if key in declarations: return reject('DUPLICATE_SOURCE_DELTA')
        declarations[key]=d
    previous_stage=anchor_stage; previous_tests=anchor_tests; previous={}; applied=[]; stages=[]
    for record in records:
        if record.stage!=previous_stage+1: return reject('NONCONTIGUOUS_STAGE_LINEAGE',len(stages))
        verdict=verify_strict_blob(record.blob,record.sha256,record.stage)
        if verdict.status!='STRICT_EVIDENCE_FIXTURE_UNAUTHENTICATED': return reject('LINEAGE_PACKAGE_REJECTED',len(stages))
        with zipfile.ZipFile(BytesIO(record.blob)) as archive:
            state=strict_json(archive.read(f'CHECKPOINT_F3_INT{record.stage}.json'))
            current=state['regression']['tests']
            if current!=previous_tests+state['new_tests']['tests']: return reject('TEST_COUNT_LINEAGE_MISMATCH',len(stages))
            sources={name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if source_path(name)}
        if set(previous)-set(sources): return reject('PRIOR_SOURCE_REMOVED',len(stages))
        for name,before in previous.items():
            after=sources[name]
            if before==after: continue
            key=(record.stage,name); declaration=declarations.get(key)
            if declaration is None: return reject('UNDECLARED_SOURCE_DELTA',len(stages))
            if (declaration.before,declaration.after)!=(before,after): return reject('SOURCE_DELTA_HASH_MISMATCH',len(stages))
            applied.append(key)
        stages.append((record.stage,current,record.sha256))
        previous_stage=record.stage; previous_tests=current; previous=sources
    if set(declarations)!=set(applied): return reject('UNUSED_SOURCE_DELTA',len(stages))
    return DeltaLineageResult('DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED',len(stages),
                              stages=tuple(stages),final_tests=previous_tests,applied=tuple(applied))


def safe_to_promote(*args,**kwargs): return False
