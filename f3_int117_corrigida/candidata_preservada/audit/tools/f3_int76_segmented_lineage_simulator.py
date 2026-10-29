"""Bounded offline lineage segments with a verified overlapping package.

Each segment starts with the preceding segment's last package, preserving source
comparisons at boundaries. This is finite caller-anchored evidence, not trust.
"""
from dataclasses import dataclass
from io import BytesIO
import re
import zipfile
from tools.f3_int62_strict_evidence_simulator import strict_json
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int74_declared_delta_simulator import SourceDelta,DeltaLineageResult,source_path
from tools.f3_int75_source_inventory_guard import verify_guarded_lineage


@dataclass(frozen=True)
class SegmentedResult(DeltaLineageResult):
    segments: tuple = ()


def verify_segments(records,deltas=(),*,anchor_stage=52,anchor_tests=526,chunk_size=8,
                    max_chunk_bytes=16777216,max_total_bytes=134217728):
    def reject(status): return SegmentedResult(status)
    if (type(anchor_stage) is not int or not 1<=anchor_stage<=9999 or type(anchor_tests) is not int or anchor_tests<1
            or type(chunk_size) is not int or not 2<=chunk_size<=32
            or type(max_chunk_bytes) is not int or not 1<=max_chunk_bytes<=33554432
            or type(max_total_bytes) is not int or not 1<=max_total_bytes<=134217728):
        return reject('INVALID_SEGMENT_BOUND')
    if (type(records) is not tuple or not 1<=len(records)<=128
            or any(type(r) is not PackageRecord or type(r.stage) is not int or type(r.blob) is not bytes for r in records)):
        return reject('INVALID_SEGMENT_RECORDS')
    if sum(len(r.blob) for r in records)>max_total_bytes: return reject('SEGMENT_TOTAL_BYTE_LIMIT')
    if type(deltas) is not tuple or len(deltas)>1024: return reject('INVALID_SOURCE_DELTAS')
    declarations={}
    for d in deltas:
        if (type(d) is not SourceDelta or type(d.stage) is not int or not 1<=d.stage<=9999
                or not source_path(d.path) or type(d.reason) is not str or not d.reason.strip() or len(d.reason)>512
                or any(type(h) is not str or not re.fullmatch('[0-9a-f]{64}',h) for h in (d.before,d.after)) or d.before==d.after):
            return reject('INVALID_SOURCE_DELTAS')
        key=(d.stage,d.path)
        if key in declarations: return reject('DUPLICATE_SOURCE_DELTA')
        declarations[key]=d
    stages=[]; applied=[]; segments=[]; chunk=[]; chunk_bytes=0; overlap=False
    current_anchor_stage=anchor_stage; current_anchor_tests=anchor_tests
    def finish_chunk():
        nonlocal current_anchor_stage,current_anchor_tests
        new_stages={r.stage for r in chunk[1:] if overlap} if overlap else {r.stage for r in chunk}
        selected=tuple(d for d in deltas if d.stage in new_stages)
        verdict=verify_guarded_lineage(tuple(chunk),selected,anchor_stage=current_anchor_stage,
                                       anchor_tests=current_anchor_tests,max_total_bytes=max_chunk_bytes)
        if verdict.status!='DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED': return 'SEGMENT_'+verdict.status
        stages.extend(verdict.stages[1:] if overlap else verdict.stages)
        applied.extend(verdict.applied)
        segments.append((chunk[0].stage,chunk[-1].stage,len(chunk)))
        last=chunk[-1]
        with zipfile.ZipFile(BytesIO(last.blob)) as archive:
            state=strict_json(archive.read(f'CHECKPOINT_F3_INT{last.stage}.json'))
        current_anchor_stage=last.stage-1
        current_anchor_tests=state['regression']['tests']-state['new_tests']['tests']
        return None
    for record in records:
        if chunk and (len(chunk)>=chunk_size or chunk_bytes+len(record.blob)>max_chunk_bytes):
            if overlap and len(chunk)==1: return reject('SEGMENT_OVERLAP_BYTE_LIMIT')
            failure=finish_chunk()
            if failure: return reject(failure)
            chunk=[chunk[-1]]; chunk_bytes=len(chunk[0].blob); overlap=True
        if chunk_bytes+len(record.blob)>max_chunk_bytes: return reject('SEGMENT_OVERLAP_BYTE_LIMIT')
        chunk.append(record); chunk_bytes+=len(record.blob)
    failure=finish_chunk()
    if failure: return reject(failure)
    if set(declarations)!=set(applied): return reject('UNUSED_SOURCE_DELTA')
    return SegmentedResult('SEGMENTED_LINEAGE_FIXTURE_UNAUTHENTICATED',len(stages),stages=tuple(stages),
                           final_tests=stages[-1][1],applied=tuple(applied),segments=tuple(segments))


def safe_to_promote(*args,**kwargs): return False
