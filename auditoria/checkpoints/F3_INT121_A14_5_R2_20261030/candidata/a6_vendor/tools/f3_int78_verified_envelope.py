"""Bounded immutable package summaries under explicit offline envelope policy.

Combines manifest, portable-name, strict checkpoint/log and source inventory
checks. Expanded file limits do not change operational flags or authenticate
origin. Historical verifiers and their limits remain unchanged.
"""
from dataclasses import dataclass
from io import BytesIO
import hashlib
import math
import re
import zipfile
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int60_package_integrity_simulator import LOCKS
from a6_vendor.tools.f3_int61_portable_package_simulator import portable_name
from a6_vendor.tools.f3_int62_strict_evidence_simulator import strict_json
from a6_vendor.tools.f3_int74_declared_delta_simulator import source_path


@dataclass(frozen=True)
class EnvelopePolicy:
    max_files: int = 512
    max_bytes: int = 67108864


@dataclass(frozen=True)
class CheckpointSummary:
    stage: int
    new_tests: int
    regression: int


@dataclass(frozen=True)
class EnvelopeResult(ConcurrentResult):
    summary: object = None
    source_digests: tuple = ()


def verify_envelope(blob,expected_sha256,stage,*,policy=EnvelopePolicy()):
    def reject(status): return EnvelopeResult(status)
    if (type(policy) is not EnvelopePolicy or type(policy.max_files) is not int or not 1<=policy.max_files<=2048
            or type(policy.max_bytes) is not int or not 1<=policy.max_bytes<=67108864
            or type(stage) is not int or not 1<=stage<=9999):
        return reject('INVALID_ENVELOPE_POLICY')
    if type(blob) is not bytes or not 1<=len(blob)<=policy.max_bytes: return reject('ENVELOPE_BYTE_LIMIT')
    if type(expected_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',expected_sha256): return reject('INVALID_ENVELOPE_DIGEST')
    if hashlib.sha256(blob).hexdigest()!=expected_sha256: return reject('ENVELOPE_DIGEST_MISMATCH')
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            entries=archive.infolist(); names=[e.filename for e in entries]
            if not entries or len(entries)>policy.max_files or sum(e.file_size for e in entries)>policy.max_bytes:
                return reject('ENVELOPE_ARCHIVE_LIMIT')
            if (len(set(n.casefold() for n in names))!=len(names)
                    or any(not portable_name(n) for n in names) or any(e.orig_filename!=e.filename for e in entries)):
                return reject('ENVELOPE_NAME_REJECTED')
            keys={n.casefold() for n in names}
            if any('/'.join(n.casefold().split('/')[:i]) in keys for n in names for i in range(1,len(n.split('/')))):
                return reject('ENVELOPE_NAME_REJECTED')
            if any(e.flag_bits&1 or (e.external_attr>>16)&0o170000==0o120000 for e in entries):
                return reject('ENVELOPE_ENTRY_REJECTED')
            for n in names:
                folded=n.casefold()
                if folded.startswith(('tests/','tools/')) and folded.endswith('.py') and not source_path(n):
                    return reject('ENVELOPE_SOURCE_NAME_REJECTED')
            manifest_name=f'SHA256_F3_INT{stage}.txt'
            manifest={}
            for line in archive.read(manifest_name).decode('utf-8').splitlines():
                digest,name=line.split('  ',1)
                if not re.fullmatch('[0-9a-f]{64}',digest) or not portable_name(name) or name in manifest or name==manifest_name:
                    return reject('ENVELOPE_MANIFEST_REJECTED')
                manifest[name]=digest
            if set(manifest)!=set(names)-{manifest_name}: return reject('ENVELOPE_MANIFEST_COVERAGE')
            for name,digest in manifest.items():
                if hashlib.sha256(archive.read(name)).hexdigest()!=digest: return reject('ENVELOPE_MANIFEST_DIGEST')
            state=strict_json(archive.read(f'CHECKPOINT_F3_INT{stage}.json'))
            if type(state) is not dict or state!=strict_json(archive.read('ULTIMO_MARCO.json')):
                return reject('ENVELOPE_CHECKPOINT_MISMATCH')
            if (state.get('last_completed')!=f'F3-INT-{stage}' or state.get('f3')!='OPEN'
                    or state.get('offline') is not True or state.get('simulation_only') is not True or state.get('certification') is not False
                    or type(state.get('locks')) is not dict or set(state['locks'])!=set(LOCKS)
                    or any(v is not False for v in state['locks'].values())):
                return reject('ENVELOPE_FLAGS_REJECTED')
            counts=[]
            for key,suffix in (('new_tests','NOVOS'),('regression','REGRESSAO')):
                data=state.get(key)
                if (type(data) is not dict or type(data.get('tests')) is not int or not 1<=data['tests']<=10000000
                        or any(type(data.get(k)) is not int or data[k]!=0 for k in ('failures','errors','skipped'))
                        or type(data.get('seconds')) not in (int,float) or data['seconds']<0 or not math.isfinite(data['seconds'])
                        or data.get('log')!=f'LOG_F3_INT{stage}_{suffix}.txt'):
                    return reject('ENVELOPE_TEST_EVIDENCE_REJECTED')
                log=archive.read(data['log']).decode('utf-8')
                summaries=re.findall(r'^Ran (\d+) tests? in ([0-9.]+)s\s*$',log,re.MULTILINE)
                if (len(summaries)!=1 or int(summaries[0][0])!=data['tests']
                        or len(re.findall(r'^OK\s*$',log,re.MULTILINE))!=1 or not log.rstrip().endswith('\nOK')
                        or re.search(r'^(?:FAILED\b|ERROR:|FAIL:|Traceback \()',log,re.MULTILINE)):
                    return reject('ENVELOPE_TEST_LOG_REJECTED')
                if not math.isfinite(float(summaries[0][1])): return reject('ENVELOPE_TEST_LOG_REJECTED')
                counts.append(data['tests'])
            if counts[1]<counts[0]: return reject('ENVELOPE_TEST_EVIDENCE_REJECTED')
            sources=tuple(sorted((n,d) for n,d in manifest.items() if source_path(n)))
            return EnvelopeResult('VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED',len(manifest),
                                  summary=CheckpointSummary(stage,*counts),source_digests=sources)
    except (zipfile.BadZipFile,ValueError,KeyError,TypeError,UnicodeError,RuntimeError,NotImplementedError,RecursionError,OverflowError):
        return reject('INVALID_ENVELOPE_STRUCTURE')


def safe_to_promote(*args,**kwargs): return False
