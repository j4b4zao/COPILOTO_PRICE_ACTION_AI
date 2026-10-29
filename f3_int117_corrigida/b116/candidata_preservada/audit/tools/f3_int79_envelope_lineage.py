"""Finite lineage over immutable verified envelopes, with declared replacements."""
from dataclasses import dataclass
import re
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int74_declared_delta_simulator import SourceDelta,DeltaLineageResult,source_path
from tools.f3_int78_verified_envelope import EnvelopePolicy,verify_envelope


@dataclass(frozen=True)
class EnvelopeLineageResult(DeltaLineageResult):
    policy: EnvelopePolicy = EnvelopePolicy()


def verify_envelope_lineage(records,deltas=(),*,anchor_stage=52,anchor_tests=526,
                             policy=EnvelopePolicy(),max_total_bytes=134217728):
    def reject(status,checked=0): return EnvelopeLineageResult(status,checked,policy=policy)
    if (type(anchor_stage) is not int or not 1<=anchor_stage<=9999 or type(anchor_tests) is not int or anchor_tests<1
            or type(max_total_bytes) is not int or not 1<=max_total_bytes<=134217728
            or type(policy) is not EnvelopePolicy or type(policy.max_files) is not int or not 1<=policy.max_files<=2048
            or type(policy.max_bytes) is not int or not 1<=policy.max_bytes<=67108864):
        return reject('INVALID_ENVELOPE_LINEAGE_BOUND')
    if (type(records) is not tuple or not 1<=len(records)<=128
            or any(type(r) is not PackageRecord or type(r.stage) is not int or type(r.blob) is not bytes for r in records)):
        return reject('INVALID_ENVELOPE_LINEAGE_RECORDS')
    if sum(len(r.blob) for r in records)>max_total_bytes: return reject('ENVELOPE_LINEAGE_BYTE_LIMIT')
    if type(deltas) is not tuple or len(deltas)>1024: return reject('INVALID_SOURCE_DELTAS')
    declarations={}
    for d in deltas:
        if (type(d) is not SourceDelta or type(d.stage) is not int or not 1<=d.stage<=9999 or not source_path(d.path)
                or type(d.reason) is not str or not d.reason.strip() or len(d.reason)>512
                or any(type(h) is not str or not re.fullmatch('[0-9a-f]{64}',h) for h in (d.before,d.after)) or d.before==d.after):
            return reject('INVALID_SOURCE_DELTAS')
        key=(d.stage,d.path)
        if key in declarations: return reject('DUPLICATE_SOURCE_DELTA')
        declarations[key]=d
    previous_stage=anchor_stage; previous_tests=anchor_tests; previous={}; stages=[]; applied=[]
    for record in records:
        if record.stage!=previous_stage+1: return reject('NONCONTIGUOUS_STAGE_LINEAGE',len(stages))
        envelope=verify_envelope(record.blob,record.sha256,record.stage,policy=policy)
        if envelope.status!='VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED': return reject('LINEAGE_'+envelope.status,len(stages))
        if envelope.summary.regression!=previous_tests+envelope.summary.new_tests:
            return reject('TEST_COUNT_LINEAGE_MISMATCH',len(stages))
        sources=dict(envelope.source_digests)
        if set(previous)-set(sources): return reject('PRIOR_SOURCE_REMOVED',len(stages))
        for name,before in previous.items():
            if sources[name]==before: continue
            key=(record.stage,name); d=declarations.get(key)
            if d is None: return reject('UNDECLARED_SOURCE_DELTA',len(stages))
            if (d.before,d.after)!=(before,sources[name]): return reject('SOURCE_DELTA_HASH_MISMATCH',len(stages))
            applied.append(key)
        previous_stage=record.stage; previous_tests=envelope.summary.regression; previous=sources
        stages.append((record.stage,previous_tests,record.sha256))
    if set(declarations)!=set(applied): return reject('UNUSED_SOURCE_DELTA',len(stages))
    return EnvelopeLineageResult('ENVELOPE_LINEAGE_FIXTURE_UNAUTHENTICATED',len(stages),stages=tuple(stages),
                                  final_tests=previous_tests,applied=tuple(applied),policy=policy)


def safe_to_promote(*args,**kwargs): return False
