"""Finite caller-anchored lineage verification of offline audit packages.

Checks continuity of counts and prior test/tool bytes in addition to each
package's integrity. Caller-provided anchors do not establish authenticity.
"""
from dataclasses import dataclass
from io import BytesIO
import hashlib
import zipfile
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int62_strict_evidence_simulator import verify_strict_blob, strict_json


@dataclass(frozen=True)
class PackageRecord:
    stage: int
    blob: bytes
    sha256: str


@dataclass(frozen=True)
class LineageResult(ConcurrentResult):
    stages: tuple = ()
    final_tests: int = 0


def verify_lineage(records,*,anchor_stage=52,anchor_tests=526,max_total_bytes=33554432):
    if (type(anchor_stage) is not int or not 1<=anchor_stage<=9999
            or type(anchor_tests) is not int or anchor_tests<1
            or type(max_total_bytes) is not int or not 1<=max_total_bytes<=33554432):
        return LineageResult('INVALID_LINEAGE_BOUND')
    if (type(records) is not tuple or not 1<=len(records)<=32
            or any(type(r) is not PackageRecord or type(r.stage) is not int
                   or type(r.blob) is not bytes for r in records)):
        return LineageResult('INVALID_LINEAGE_RECORDS')
    if sum(len(r.blob) for r in records)>max_total_bytes:
        return LineageResult('LINEAGE_BYTE_LIMIT_EXCEEDED')
    previous_stage=anchor_stage; previous_tests=anchor_tests; previous_sources={}; stages=[]
    for record in records:
        if record.stage!=previous_stage+1:
            return LineageResult('NONCONTIGUOUS_STAGE_LINEAGE',len(stages))
        verdict=verify_strict_blob(record.blob,record.sha256,record.stage)
        if verdict.status!='STRICT_EVIDENCE_FIXTURE_UNAUTHENTICATED':
            return LineageResult('LINEAGE_PACKAGE_REJECTED',len(stages))
        with zipfile.ZipFile(BytesIO(record.blob)) as archive:
            checkpoint=strict_json(archive.read(f'CHECKPOINT_F3_INT{record.stage}.json'))
            current=checkpoint['regression']['tests']; added=checkpoint['new_tests']['tests']
            if current!=previous_tests+added:
                return LineageResult('TEST_COUNT_LINEAGE_MISMATCH',len(stages))
            sources={name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
                     if name.startswith(('tests/','tools/')) and name.endswith('.py')}
            if any(sources.get(name)!=digest for name,digest in previous_sources.items()):
                return LineageResult('PRIOR_SOURCE_LINEAGE_MISMATCH',len(stages))
        stages.append((record.stage,current,record.sha256))
        previous_stage=record.stage; previous_tests=current; previous_sources=sources
    return LineageResult('PACKAGE_LINEAGE_FIXTURE_UNAUTHENTICATED',len(stages),stages=tuple(stages),final_tests=previous_tests)


def safe_to_promote(*args,**kwargs):
    return False
