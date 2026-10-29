"""Closed JSON import-witness references; package bytes supplied in a bounded catalog.

Catalog hashes and pins are caller fixtures, not signatures or authentication.
No package path is opened on disk, and no class is loaded from JSON.
"""
from dataclasses import asdict,dataclass
import hashlib
import json
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int62_strict_evidence_simulator import strict_json
from tools.f3_int70_crash_witness_codec import wire_scan,MAX_BYTES
from tools.f3_int72_atomic_witness_batch_simulator import Registry,digest_valid
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int82_atomic_package_witness_batch import PackageWitnessRequest
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot,valid_snapshot,valid_requests
from tools.f3_int84_import_schedule_divergence import run_import_schedule
from tools.f3_int88_import_divergence_witness import ImportWitness,replay_import_witness,classify_import_ends


@dataclass(frozen=True)
class EncodedImportResult(ConcurrentResult):
    classification: str = ''


def run_digest(trace):
    blob=json.dumps(asdict(trace),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(blob).hexdigest()


def encode_import_witness(witness):
    checked=replay_import_witness(witness)
    if checked.status!='IMPORT_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED': raise ValueError(checked.status)
    payload=dict(schema=1,initial=dict(version=witness.initial.version,digests=list(witness.initial.registry.digests)),
                 batches=[[dict(stage=r.record.stage,package_sha256=r.record.sha256,path=r.path,canonical_pin=r.canonical_pin) for r in batch]
                          for batch in witness.batches],
                 left_events=[list(e) for e in witness.left.schedule],right_events=[list(e) for e in witness.right.schedule],
                 left_trace_sha256=run_digest(witness.left),right_trace_sha256=run_digest(witness.right))
    wire_scan(payload)
    blob=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(blob)>MAX_BYTES: raise ValueError('IMPORT_WIRE_BYTE_LIMIT')
    return blob


def decode_import_witness(blob,catalog):
    if type(blob) is not bytes or not 1<=len(blob)<=MAX_BYTES: raise ValueError('IMPORT_WIRE_BYTE_LIMIT')
    if (type(catalog) is not tuple or not 1<=len(catalog)<=48
            or any(type(r) is not PackageRecord or type(r.stage) is not int or not 1<=r.stage<=9999
                   or type(r.blob) is not bytes or not digest_valid(r.sha256) for r in catalog)):
        raise ValueError('INVALID_IMPORT_CATALOG')
    if sum(len(r.blob) for r in catalog)>33554432: raise ValueError('IMPORT_CATALOG_BYTE_LIMIT')
    records={}
    for record in catalog:
        if record.sha256 in records: raise ValueError('DUPLICATE_IMPORT_CATALOG_DIGEST')
        if hashlib.sha256(record.blob).hexdigest()!=record.sha256: raise ValueError('IMPORT_CATALOG_DIGEST_MISMATCH')
        records[record.sha256]=record
    try:
        payload=strict_json(blob); wire_scan(payload)
        if (type(payload) is not dict or set(payload)!={'schema','initial','batches','left_events','right_events','left_trace_sha256','right_trace_sha256'}
                or type(payload['schema']) is not int or payload['schema']!=1):
            raise ValueError('INVALID_IMPORT_WIRE_SCHEMA')
        initial=payload['initial']
        if type(initial) is not dict or set(initial)!={'version','digests'} or type(initial['digests']) is not list:
            raise ValueError('INVALID_IMPORT_WIRE_INITIAL')
        snapshot=RegistrySnapshot(initial['version'],Registry(tuple(initial['digests'])))
        if not valid_snapshot(snapshot): raise ValueError('INVALID_IMPORT_WIRE_INITIAL')
        if type(payload['batches']) is not list or not 1<=len(payload['batches'])<=3:
            raise ValueError('INVALID_IMPORT_WIRE_BATCHES')
        batches=[]; used=set()
        for batch in payload['batches']:
            if type(batch) is not list or not 1<=len(batch)<=16: raise ValueError('INVALID_IMPORT_WIRE_BATCH')
            requests=[]
            for ref in batch:
                if type(ref) is not dict or set(ref)!={'stage','package_sha256','path','canonical_pin'}:
                    raise ValueError('INVALID_IMPORT_WIRE_REFERENCE')
                if not digest_valid(ref['package_sha256']) or type(ref['stage']) is not int:
                    raise ValueError('INVALID_IMPORT_WIRE_REFERENCE')
                record=records.get(ref['package_sha256'])
                if record is None or record.stage!=ref['stage']: raise ValueError('MISSING_OR_WRONG_IMPORT_CATALOG_RECORD')
                used.add(record.sha256); requests.append(PackageWitnessRequest(record,ref['path'],ref['canonical_pin']))
            requests=tuple(requests)
            if not valid_requests(requests): raise ValueError('INVALID_IMPORT_WIRE_REQUESTS')
            batches.append(requests)
        if used!=set(records): raise ValueError('UNUSED_IMPORT_CATALOG_RECORD')
        batches=tuple(batches); traces=[]
        for side in ('left','right'):
            events=payload[side+'_events']; expected=payload[side+'_trace_sha256']
            if (type(events) is not list or len(events)!=2*len(batches) or not digest_valid(expected)
                    or any(type(e) is not list or len(e)!=2 or type(e[0]) is not str or type(e[1]) is not int for e in events)):
                raise ValueError('INVALID_IMPORT_WIRE_EVENTS')
            trace=run_import_schedule(snapshot,batches,tuple(tuple(e) for e in events))
            if run_digest(trace)!=expected: raise ValueError('IMPORT_WIRE_TRACE_DIGEST_MISMATCH')
            traces.append(trace)
        witness=ImportWitness(snapshot,batches,*traces)
        if replay_import_witness(witness).status!='IMPORT_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED':
            raise ValueError('IMPORT_WIRE_DIVERGENCE_NOT_REPRODUCED')
        return witness
    except (TypeError,KeyError,UnicodeError,RecursionError,OverflowError) as error:
        raise ValueError('INVALID_IMPORT_WIRE_STRUCTURE') from error


def assess_encoded_import(blob,catalog):
    try:
        witness=decode_import_witness(blob,catalog)
    except ValueError:
        return EncodedImportResult('ENCODED_IMPORT_WITNESS_REJECTED')
    classification=classify_import_ends(witness.left.snapshots[-1],witness.right.snapshots[-1])
    return EncodedImportResult('ENCODED_IMPORT_WITNESS_REPLAYED_FIXTURE_UNAUTHENTICATED',2,classification=classification)


def safe_to_promote(*args,**kwargs): return False
