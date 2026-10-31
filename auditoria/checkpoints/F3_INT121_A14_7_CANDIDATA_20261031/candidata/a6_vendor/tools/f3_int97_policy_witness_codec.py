"""Closed schema=2 references for replay under a pinned caller policy context.

Historical schema=1 is separate. Catalogs and resource policies remain caller
fixtures; replay consistency never authenticates or authorizes operations.
"""
from dataclasses import dataclass
import hashlib
import json
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int62_strict_evidence_simulator import strict_json
from a6_vendor.tools.f3_int70_crash_witness_codec import MAX_BYTES,wire_scan
from a6_vendor.tools.f3_int72_atomic_witness_batch_simulator import Registry,digest_valid
from a6_vendor.tools.f3_int73_package_lineage_simulator import PackageRecord
from a6_vendor.tools.f3_int78_verified_envelope import EnvelopePolicy
from a6_vendor.tools.f3_int82_atomic_package_witness_batch import PackageWitnessRequest
from a6_vendor.tools.f3_int83_concurrent_import_simulator import valid_requests
from a6_vendor.tools.f3_int86_policy_bound_import import PolicySnapshot,valid_policy_snapshot
from a6_vendor.tools.f3_int88_import_divergence_witness import classify_import_ends
from a6_vendor.tools.f3_int89_import_witness_codec import run_digest
from a6_vendor.tools.f3_int95_policy_import_schedules import run_policy_schedule
from a6_vendor.tools.f3_int96_policy_import_witness import PolicyImportWitness,replay_policy_witness


@dataclass(frozen=True)
class EncodedPolicyResult(ConcurrentResult):
    classification: str = ''


def encode_policy_witness(witness):
    checked=replay_policy_witness(witness)
    if checked.status!='POLICY_IMPORT_DIVERGENCE_FIXTURE_UNAUTHENTICATED': raise ValueError(checked.status)
    s=witness.initial
    payload=dict(schema=2,initial=dict(version=s.version,digests=list(s.registry.digests),
                                     policy=dict(max_files=s.policy.max_files,max_bytes=s.policy.max_bytes)),
                 batches=[[dict(stage=r.record.stage,package_sha256=r.record.sha256,path=r.path,canonical_pin=r.canonical_pin) for r in b] for b in witness.batches],
                 left_events=[list(e) for e in witness.left.schedule],right_events=[list(e) for e in witness.right.schedule],
                 left_trace_sha256=run_digest(witness.left),right_trace_sha256=run_digest(witness.right))
    wire_scan(payload)
    blob=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(blob)>MAX_BYTES: raise ValueError('POLICY_WIRE_BYTE_LIMIT')
    return blob


def decode_policy_witness(blob,catalog):
    if type(blob) is not bytes or not 1<=len(blob)<=MAX_BYTES: raise ValueError('POLICY_WIRE_BYTE_LIMIT')
    if (type(catalog) is not tuple or not 1<=len(catalog)<=48
            or any(type(r) is not PackageRecord or type(r.stage) is not int or not 1<=r.stage<=9999
                   or type(r.blob) is not bytes or not digest_valid(r.sha256) for r in catalog)):
        raise ValueError('INVALID_POLICY_CATALOG')
    if sum(len(r.blob) for r in catalog)>33554432: raise ValueError('POLICY_CATALOG_BYTE_LIMIT')
    records={}
    for record in catalog:
        if record.sha256 in records or hashlib.sha256(record.blob).hexdigest()!=record.sha256:
            raise ValueError('POLICY_CATALOG_DIGEST_REJECTED')
        records[record.sha256]=record
    try:
        p=strict_json(blob); wire_scan(p)
        if (type(p) is not dict or set(p)!={'schema','initial','batches','left_events','right_events','left_trace_sha256','right_trace_sha256'}
                or type(p['schema']) is not int or p['schema']!=2): raise ValueError('INVALID_POLICY_WIRE_SCHEMA')
        initial=p['initial']
        if (type(initial) is not dict or set(initial)!={'version','digests','policy'} or type(initial['digests']) is not list
                or type(initial['policy']) is not dict or set(initial['policy'])!={'max_files','max_bytes'}):
            raise ValueError('INVALID_POLICY_WIRE_CONTEXT')
        snapshot=PolicySnapshot(initial['version'],Registry(tuple(initial['digests'])),EnvelopePolicy(**initial['policy']))
        if not valid_policy_snapshot(snapshot): raise ValueError('INVALID_POLICY_WIRE_CONTEXT')
        if type(p['batches']) is not list or not 1<=len(p['batches'])<=3: raise ValueError('INVALID_POLICY_WIRE_BATCHES')
        batches=[]; used=set()
        for batch in p['batches']:
            if type(batch) is not list or not 1<=len(batch)<=16: raise ValueError('INVALID_POLICY_WIRE_BATCH')
            requests=[]
            for ref in batch:
                if (type(ref) is not dict or set(ref)!={'stage','package_sha256','path','canonical_pin'}
                        or type(ref['stage']) is not int or not digest_valid(ref['package_sha256'])):
                    raise ValueError('INVALID_POLICY_WIRE_REFERENCE')
                record=records.get(ref['package_sha256'])
                if record is None or record.stage!=ref['stage']: raise ValueError('MISSING_POLICY_CATALOG_REFERENCE')
                used.add(record.sha256); requests.append(PackageWitnessRequest(record,ref['path'],ref['canonical_pin']))
            requests=tuple(requests)
            if not valid_requests(requests): raise ValueError('INVALID_POLICY_WIRE_REQUEST')
            batches.append(requests)
        if used!=set(records): raise ValueError('UNUSED_POLICY_CATALOG_REFERENCE')
        batches=tuple(batches); traces=[]
        for side in ('left','right'):
            events=p[side+'_events']; expected=p[side+'_trace_sha256']
            if (type(events) is not list or len(events)!=2*len(batches) or not digest_valid(expected)
                    or any(type(e) is not list or len(e)!=2 or type(e[0]) is not str or type(e[1]) is not int for e in events)):
                raise ValueError('INVALID_POLICY_WIRE_EVENTS')
            trace=run_policy_schedule(snapshot,batches,tuple(tuple(e) for e in events))
            if run_digest(trace)!=expected: raise ValueError('POLICY_WIRE_TRACE_MISMATCH')
            traces.append(trace)
        witness=PolicyImportWitness(snapshot,batches,*traces)
        if replay_policy_witness(witness).status!='POLICY_IMPORT_DIVERGENCE_FIXTURE_UNAUTHENTICATED':
            raise ValueError('POLICY_WIRE_DIVERGENCE_NOT_REPRODUCED')
        return witness
    except (TypeError,KeyError,UnicodeError,RecursionError,OverflowError) as error:
        raise ValueError('INVALID_POLICY_WIRE_STRUCTURE') from error


def assess_encoded_policy(blob,catalog):
    try: witness=decode_policy_witness(blob,catalog)
    except ValueError: return EncodedPolicyResult('ENCODED_POLICY_WITNESS_REJECTED')
    return EncodedPolicyResult('ENCODED_POLICY_WITNESS_REPLAYED_FIXTURE_UNAUTHENTICATED',2,
                                classification=classify_import_ends(witness.left.snapshots[-1],witness.right.snapshots[-1]))


def safe_to_promote(*args,**kwargs): return False
