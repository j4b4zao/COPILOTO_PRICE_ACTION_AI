"""Offline byte-level package verifier. Hashes do not establish authenticity."""
from io import BytesIO
import hashlib
import json
import re
import zipfile
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult

LOCKS=('orders_allowed','live_certified','flow_complete','f3_resolved',
       'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified')


def safe_name(name):
    return (type(name) is str and bool(name) and not any(c in name for c in ('\\',':','\x00'))
            and all(part not in ('','.','..') for part in name.split('/')))


def verify_blob(blob, expected_sha256, stage, *, max_bytes=64*1024*1024, max_files=512):
    def result(status,count=0): return ConcurrentResult(status,count)
    if (type(max_bytes) is not int or not 1<=max_bytes<=64*1024*1024
            or type(max_files) is not int or not 1<=max_files<=512
            or type(stage) is not int or not 1<=stage<=9999):
        return result('INVALID_PACKAGE_BOUND')
    if type(blob) is not bytes or len(blob)>max_bytes:
        return result('INVALID_OR_OVERSIZED_PACKAGE')
    if type(expected_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',expected_sha256):
        return result('INVALID_EXPECTED_DIGEST')
    if hashlib.sha256(blob).hexdigest()!=expected_sha256:
        return result('PACKAGE_DIGEST_MISMATCH')
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            entries=archive.infolist()
            names=[e.filename for e in entries]
            if (not entries or len(entries)>max_files or sum(e.file_size for e in entries)>max_bytes):
                return result('ARCHIVE_LIMIT_EXCEEDED')
            if (len(set(names))!=len(names) or any(not safe_name(n) for n in names)
                    or any(e.orig_filename!=e.filename for e in entries)):
                return result('UNSAFE_OR_DUPLICATE_ARCHIVE_NAME')
            if any(e.flag_bits & 1 or (e.external_attr>>16)&0o170000==0o120000 for e in entries):
                return result('UNSUPPORTED_ARCHIVE_ENTRY')
            manifest_name=f'SHA256_F3_INT{stage}.txt'
            if manifest_name not in names:
                return result('MISSING_STAGE_MANIFEST')
            records={}
            for line in archive.read(manifest_name).decode('utf-8').splitlines():
                digest,name=line.split('  ',1)
                if (not re.fullmatch('[0-9a-f]{64}',digest) or not safe_name(name)
                        or name in records or name==manifest_name):
                    return result('INVALID_STAGE_MANIFEST')
                records[name]=digest
            if set(records)!=set(names)-{manifest_name}:
                return result('MANIFEST_COVERAGE_MISMATCH')
            for name,digest in records.items():
                if hashlib.sha256(archive.read(name)).hexdigest()!=digest:
                    return result('MANIFEST_DIGEST_MISMATCH')
            state=json.loads(archive.read(f'CHECKPOINT_F3_INT{stage}.json'))
            if type(state) is not dict:
                return result('INVALID_PACKAGE_STRUCTURE')
            if state!=json.loads(archive.read('ULTIMO_MARCO.json')):
                return result('LATEST_CHECKPOINT_MISMATCH')
            if (state.get('last_completed')!=f'F3-INT-{stage}' or state.get('f3')!='OPEN'
                    or state.get('offline') is not True or state.get('simulation_only') is not True
                    or state.get('certification') is not False
                    or type(state.get('locks')) is not dict or set(state['locks'])!=set(LOCKS)
                    or any(v is not False for v in state['locks'].values())):
                return result('UNSAFE_CHECKPOINT_FLAGS')
            for field,suffix in (('new_tests','NOVOS'),('regression','REGRESSAO')):
                summary=state.get(field)
                if (type(summary) is not dict or type(summary.get('tests')) is not int or summary['tests']<=0
                        or any(type(summary.get(k)) is not int or summary[k]!=0 for k in ('failures','errors','skipped'))
                        or summary.get('log')!=f'LOG_F3_INT{stage}_{suffix}.txt'):
                    return result('INVALID_TEST_EVIDENCE')
                log=archive.read(summary['log']).decode('utf-8')
                if (not re.search(r'\bRan '+str(summary['tests'])+r' tests? in ',log)
                        or not log.rstrip().endswith('\nOK')):
                    return result('TEST_LOG_MISMATCH')
            if state['regression']['tests']<state['new_tests']['tests']:
                return result('INVALID_TEST_EVIDENCE')
            return result('PACKAGE_FIXTURE_INTEGRITY_VERIFIED_UNAUTHENTICATED',len(records))
    except (zipfile.BadZipFile,RuntimeError,KeyError,ValueError,UnicodeError,TypeError,NotImplementedError,RecursionError):
        return result('INVALID_PACKAGE_STRUCTURE')


def safe_to_promote(*args, **kwargs):
    return False
