"""Closed deterministic ZIP transport for offline import witness JSON and catalog.

Only byte buffers are read; nothing is extracted or executed. Hashes are caller
pins, not signatures. Fixed ZIP timestamps do not attest a creation time.
"""
from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import zipfile
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int61_portable_package_simulator import portable_name
from tools.f3_int62_strict_evidence_simulator import strict_json
from tools.f3_int70_crash_witness_codec import MAX_BYTES,wire_scan
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int88_import_divergence_witness import classify_import_ends
from tools.f3_int89_import_witness_codec import encode_import_witness,decode_import_witness

MAX_BUNDLE_BYTES=33554432+2*MAX_BYTES


@dataclass(frozen=True)
class BundleResult(ConcurrentResult):
    classification: str = ''
    bundle_sha256: str = ''


def encode_import_bundle(witness):
    payload=encode_import_witness(witness); catalog={}
    for batch in witness.batches:
        for request in batch:
            record=request.record
            if record.sha256 in catalog and catalog[record.sha256]!=record:
                raise ValueError('AMBIGUOUS_BUNDLE_CATALOG')
            catalog[record.sha256]=record
    records=tuple(catalog[key] for key in sorted(catalog))
    decode_import_witness(payload,records)
    descriptor=dict(schema=1,witness_sha256=hashlib.sha256(payload).hexdigest(),
                    records=[dict(stage=r.stage,sha256=r.sha256,file=f'catalog/{r.sha256}.zip') for r in records])
    descriptor=json.dumps(descriptor,sort_keys=True,separators=(',',':')).encode('ascii')
    files={'witness.json':payload,'bundle_manifest.json':descriptor}
    files.update((f'catalog/{r.sha256}.zip',r.blob) for r in records)
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3; info.external_attr=0o100600<<16
            archive.writestr(info,files[name])
    blob=stream.getvalue()
    if len(blob)>MAX_BUNDLE_BYTES: raise ValueError('BUNDLE_BYTE_LIMIT')
    return blob


def decode_import_bundle(blob,expected_sha256):
    if type(blob) is not bytes or not 1<=len(blob)<=MAX_BUNDLE_BYTES: raise ValueError('BUNDLE_BYTE_LIMIT')
    if not digest_valid(expected_sha256) or hashlib.sha256(blob).hexdigest()!=expected_sha256:
        raise ValueError('BUNDLE_DIGEST_MISMATCH')
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            entries=archive.infolist(); names=[e.filename for e in entries]
            if not 3<=len(entries)<=50 or sum(e.file_size for e in entries)>MAX_BUNDLE_BYTES:
                raise ValueError('BUNDLE_ARCHIVE_LIMIT')
            if (len(set(names))!=len(names) or any(not portable_name(n) for n in names)
                    or any(e.orig_filename!=e.filename or e.flag_bits&1 or (e.external_attr>>16)&0o170000==0o120000 for e in entries)):
                raise ValueError('BUNDLE_ENTRY_REJECTED')
            info={e.filename:e for e in entries}
            if info['witness.json'].file_size>MAX_BYTES or info['bundle_manifest.json'].file_size>MAX_BYTES:
                raise ValueError('BUNDLE_JSON_BYTE_LIMIT')
            descriptor=strict_json(archive.read('bundle_manifest.json')); wire_scan(descriptor)
            if (type(descriptor) is not dict or set(descriptor)!={'schema','witness_sha256','records'}
                    or type(descriptor['schema']) is not int or descriptor['schema']!=1
                    or not digest_valid(descriptor['witness_sha256']) or type(descriptor['records']) is not list
                    or not 1<=len(descriptor['records'])<=48):
                raise ValueError('INVALID_BUNDLE_MANIFEST')
            payload=archive.read('witness.json')
            if hashlib.sha256(payload).hexdigest()!=descriptor['witness_sha256']: raise ValueError('BUNDLE_WITNESS_DIGEST_MISMATCH')
            expected={'witness.json','bundle_manifest.json'}; catalog=[]; digests=set()
            for item in descriptor['records']:
                if (type(item) is not dict or set(item)!={'stage','sha256','file'} or type(item['stage']) is not int
                        or not 1<=item['stage']<=9999 or not digest_valid(item['sha256'])
                        or item['file']!=f'catalog/{item["sha256"]}.zip' or item['sha256'] in digests):
                    raise ValueError('INVALID_BUNDLE_CATALOG')
                expected.add(item['file']); digests.add(item['sha256']); package=archive.read(item['file'])
                if hashlib.sha256(package).hexdigest()!=item['sha256']: raise ValueError('BUNDLE_CATALOG_DIGEST_MISMATCH')
                catalog.append(PackageRecord(item['stage'],package,item['sha256']))
            if set(names)!=expected: raise ValueError('BUNDLE_COVERAGE_MISMATCH')
        return decode_import_witness(payload,tuple(catalog))
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RuntimeError,NotImplementedError,RecursionError,OverflowError) as error:
        raise ValueError('INVALID_BUNDLE_STRUCTURE') from error


def assess_import_bundle(blob,expected_sha256):
    try:
        witness=decode_import_bundle(blob,expected_sha256)
    except ValueError:
        return BundleResult('IMPORT_BUNDLE_REJECTED')
    return BundleResult('IMPORT_BUNDLE_REPLAYED_FIXTURE_UNAUTHENTICATED',2,
                         classification=classify_import_ends(witness.left.snapshots[-1],witness.right.snapshots[-1]),
                         bundle_sha256=expected_sha256)


def safe_to_promote(*args,**kwargs): return False
