"""Reject ambiguous checkpoint JSON and contradictory finite test logs offline."""
from io import BytesIO
import json
import math
import re
import zipfile
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int61_portable_package_simulator import verify_portable_blob


def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def constant(value): raise ValueError('nonfinite JSON constant')
    def floating(value):
        parsed=float(value)
        if not math.isfinite(parsed): raise ValueError('nonfinite JSON float')
        return parsed
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant,parse_float=floating)


def verify_strict_blob(blob,expected_sha256,stage,**bounds):
    verified=verify_portable_blob(blob,expected_sha256,stage,**bounds)
    if verified.status!='PORTABLE_PACKAGE_FIXTURE_UNAUTHENTICATED':
        return verified
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            state=strict_json(archive.read(f'CHECKPOINT_F3_INT{stage}.json'))
            if state!=strict_json(archive.read('ULTIMO_MARCO.json')):
                return ConcurrentResult('STRICT_CHECKPOINT_MISMATCH')
            for name in ('new_tests','regression'):
                summary=state[name]; seconds=summary.get('seconds')
                if type(seconds) not in (int,float) or seconds<0 or not math.isfinite(seconds):
                    return ConcurrentResult('INVALID_TEST_DURATION')
                log=archive.read(summary['log']).decode('utf-8')
                summaries=re.findall(r'^Ran (\d+) tests? in ([0-9.]+)s\s*$',log,re.MULTILINE)
                if (len(summaries)!=1 or int(summaries[0][0])!=summary['tests']
                        or len(re.findall(r'^OK\s*$',log,re.MULTILINE))!=1
                        or re.search(r'^(?:FAILED\b|ERROR:|FAIL:|Traceback \()',log,re.MULTILINE)):
                    return ConcurrentResult('AMBIGUOUS_TEST_LOG')
                elapsed=float(summaries[0][1])
                if not math.isfinite(elapsed) or elapsed<0:
                    return ConcurrentResult('INVALID_TEST_DURATION')
        return ConcurrentResult('STRICT_EVIDENCE_FIXTURE_UNAUTHENTICATED',verified.checked)
    except (ValueError,TypeError,KeyError,UnicodeError,RecursionError,OverflowError):
        return ConcurrentResult('AMBIGUOUS_CHECKPOINT_JSON')


def safe_to_promote(*args,**kwargs):
    return False
