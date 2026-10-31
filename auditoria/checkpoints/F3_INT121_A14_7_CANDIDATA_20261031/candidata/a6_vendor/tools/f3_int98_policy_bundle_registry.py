"""Offline schema2 witness ZIP and typed registry. All bytes are caller fixtures."""
from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import zipfile
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int61_portable_package_simulator import portable_name
from a6_vendor.tools.f3_int62_strict_evidence_simulator import strict_json
from a6_vendor.tools.f3_int70_crash_witness_codec import MAX_BYTES,wire_scan
from a6_vendor.tools.f3_int72_atomic_witness_batch_simulator import digest_valid
from a6_vendor.tools.f3_int73_package_lineage_simulator import PackageRecord
from a6_vendor.tools.f3_int88_import_divergence_witness import classify_import_ends
from a6_vendor.tools.f3_int90_import_witness_bundle import MAX_BUNDLE_BYTES
from a6_vendor.tools.f3_int97_policy_witness_codec import encode_policy_witness,decode_policy_witness

NAMESPACE='POLICY_WITNESS_SCHEMA2_V1'

@dataclass(frozen=True)
class PolicyBundleRecord:
    blob: bytes
    sha256: str

@dataclass(frozen=True)
class PolicyEvidenceRegistry:
    reference_ids: tuple = ()
    namespace: str = NAMESPACE

@dataclass(frozen=True)
class PolicyEvidenceReceipt:
    reference_id: str
    classification: str

@dataclass(frozen=True)
class PolicyEvidenceResult(ConcurrentResult):
    registry: PolicyEvidenceRegistry = PolicyEvidenceRegistry()
    receipts: tuple = ()

def _catalog(witness):
    records={}
    for batch in witness.batches:
        for req in batch:
            record=req.record
            if record.sha256 in records and records[record.sha256]!=record:
                raise ValueError('AMBIGUOUS_POLICY_CATALOG')
            records[record.sha256]=record
    return tuple(records[key] for key in sorted(records))

def encode_policy_bundle(witness):
    payload=encode_policy_witness(witness)
    catalog=_catalog(witness)
    decode_policy_witness(payload,catalog)
    manifest={'schema':2,'witness_sha256':hashlib.sha256(payload).hexdigest(),
              'records':[{'stage':r.stage,'sha256':r.sha256,'file':f'catalog/{r.sha256}.zip'} for r in catalog]}
    files={'witness.json':payload,'bundle_manifest.json':json.dumps(manifest,sort_keys=True,separators=(',',':')).encode('ascii')}
    files.update((f'catalog/{r.sha256}.zip',r.blob) for r in catalog)
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3
            info.external_attr=0o100600<<16
            archive.writestr(info,files[name])
    blob=stream.getvalue()
    if len(blob)>MAX_BUNDLE_BYTES: raise ValueError('POLICY_BUNDLE_BYTE_LIMIT')
    return blob

def decode_policy_bundle(blob,expected_sha256):
    if type(blob) is not bytes or not 1<=len(blob)<=MAX_BUNDLE_BYTES:
        raise ValueError('POLICY_BUNDLE_BYTE_LIMIT')
    if not digest_valid(expected_sha256) or hashlib.sha256(blob).hexdigest()!=expected_sha256:
        raise ValueError('POLICY_BUNDLE_DIGEST_MISMATCH')
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            entries=archive.infolist(); names=[e.filename for e in entries]
            if not 3<=len(entries)<=50 or sum(e.file_size for e in entries)>MAX_BUNDLE_BYTES:
                raise ValueError('POLICY_BUNDLE_ARCHIVE_LIMIT')
            if len(set(names))!=len(names) or any(not portable_name(n) or e.orig_filename!=n or e.flag_bits&1 or (e.external_attr>>16)&0o170000==0o120000 for n,e in zip(names,entries)):
                raise ValueError('POLICY_BUNDLE_ENTRY_REJECTED')
            info={e.filename:e for e in entries}
            if 'witness.json' not in info or 'bundle_manifest.json' not in info:
                raise ValueError('POLICY_BUNDLE_MISSING_META')
            if info['witness.json'].file_size>MAX_BYTES or info['bundle_manifest.json'].file_size>MAX_BYTES:
                raise ValueError('POLICY_BUNDLE_JSON_LIMIT')
            manifest=strict_json(archive.read('bundle_manifest.json')); wire_scan(manifest)
            if (type(manifest) is not dict or set(manifest)!={'schema','witness_sha256','records'}
                or type(manifest['schema']) is not int or manifest['schema']!=2
                or not digest_valid(manifest['witness_sha256']) or type(manifest['records']) is not list
                or not 1<=len(manifest['records'])<=48):
                raise ValueError('INVALID_POLICY_BUNDLE_MANIFEST')
            payload=archive.read('witness.json')
            if hashlib.sha256(payload).hexdigest()!=manifest['witness_sha256']:
                raise ValueError('POLICY_BUNDLE_WITNESS_DIGEST_MISMATCH')
            expected={'witness.json','bundle_manifest.json'}; catalog=[]; digests=set()
            for item in manifest['records']:
                if (type(item) is not dict or set(item)!={'stage','sha256','file'}
                    or type(item['stage']) is not int or not 1<=item['stage']<=9999
                    or not digest_valid(item['sha256']) or item['file']!=f'catalog/{item["sha256"]}.zip'
                    or item['sha256'] in digests):
                    raise ValueError('INVALID_POLICY_BUNDLE_CATALOG')
                expected.add(item['file']); digests.add(item['sha256'])
                package=archive.read(item['file'])
                if hashlib.sha256(package).hexdigest()!=item['sha256']:
                    raise ValueError('POLICY_BUNDLE_CATALOG_DIGEST_MISMATCH')
                catalog.append(PackageRecord(item['stage'],package,item['sha256']))
            if set(names)!=expected: raise ValueError('POLICY_BUNDLE_COVERAGE_MISMATCH')
        return decode_policy_witness(payload,tuple(catalog))
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RuntimeError,NotImplementedError,RecursionError,OverflowError) as exc:
        raise ValueError('INVALID_POLICY_BUNDLE_STRUCTURE') from exc

def valid_policy_registry(registry):
    return (type(registry) is PolicyEvidenceRegistry and registry.namespace==NAMESPACE
            and type(registry.reference_ids) is tuple and len(registry.reference_ids)<=256
            and all(digest_valid(x) for x in registry.reference_ids)
            and len(set(registry.reference_ids))==len(registry.reference_ids))

def register_policy_bundles(registry,records,*,max_total_bytes=67108864):
    def reject(status): return PolicyEvidenceResult(status,registry=registry)
    if not valid_policy_registry(registry): return reject('INVALID_POLICY_REGISTRY')
    if type(max_total_bytes) is not int or not 1<=max_total_bytes<=67108864:
        return reject('INVALID_POLICY_TOTAL_BOUND')
    if (type(records) is not tuple or not 1<=len(records)<=8 or
        any(type(r) is not PolicyBundleRecord or type(r.blob) is not bytes or not 1<=len(r.blob)<=MAX_BUNDLE_BYTES or not digest_valid(r.sha256) for r in records)):
        return reject('INVALID_POLICY_BATCH')
    if sum(len(r.blob) for r in records)>max_total_bytes: return reject('POLICY_TOTAL_BYTE_LIMIT')
    if len(registry.reference_ids)+len(records)>256: return reject('POLICY_REGISTRY_LIMIT')
    seen=set(registry.reference_ids); receipts=[]
    for record in records:
        try: witness=decode_policy_bundle(record.blob,record.sha256)
        except ValueError: return reject('POLICY_BUNDLE_REJECTED')
        reference=hashlib.sha256(NAMESPACE.encode()+b'\0REFERENCE\0'+encode_policy_witness(witness)).hexdigest()
        if reference in seen: return reject('POLICY_REFERENCE_REPLAY')
        seen.add(reference)
        receipts.append(PolicyEvidenceReceipt(reference,classify_import_ends(witness.left.snapshots[-1],witness.right.snapshots[-1])))
    updated=PolicyEvidenceRegistry(registry.reference_ids+tuple(r.reference_id for r in receipts))
    return PolicyEvidenceResult('POLICY_EVIDENCE_REGISTERED_FIXTURE_UNAUTHENTICATED',len(receipts),registry=updated,receipts=tuple(receipts))

def safe_to_promote(*args,**kwargs): return False
