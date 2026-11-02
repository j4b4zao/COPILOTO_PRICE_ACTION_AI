"""Replay captured disk bytes independently of the candidate journal comparer."""
import base64
import hashlib
import json
from pathlib import Path
import sys

import auditar_a14_7 as startup

SCENARIOS = {
    'test_valid_journal_matches_pipe_after_cleanup':'valid',
    'test_missing_journal_rejected_after_cleanup':'missing',
    'test_truncated_journal_rejected_after_cleanup':'truncated',
    'test_swapped_nonce_rejected_after_cleanup':'nonce',
    'test_swapped_identity_rejected_after_cleanup':'identity',
    'test_changed_cleanup_rejected_after_cleanup':'cleanup',
    'test_changed_authorization_rejected_after_cleanup':'authorization',
    'test_real_publication_failure_retains_pipe_fallback':'publication_failure',
}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def pairs(items):
    result = {}
    for key,value in items:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(value)


def decode(raw):
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid_constant)


def check(row, mode):
    errors = []
    def need(ok,message):
        if not ok:
            errors.append(message)
    fault = SCENARIOS.get(row.get('test'))
    need(fault is not None and row.get('fault') == fault,'Scenario mismatch')
    need(type(row.get('optimization')) is int and row['optimization'] == mode,'Wrong optimization')
    for key,value in dict(f3='OPEN',offline=True,simulation_only=True,real_operations_authorized=False,
                          runtime_modified=False,production_api_changed=False,
                          durability_tested=False,authentication_tested=False).items():
        need(type(row.get(key)) is type(value) and row.get(key) == value,'Restriction/scope changed: '+key)
    need(row.get('observer_error') is None,'Observer failed')
    native = row.get('native') or {}
    errors.extend('Native proof: '+error for error in startup.check(native,mode))
    result = native.get('result') or {}
    publication = fault == 'publication_failure'
    need(result.get('mode') == ('journal_failure' if publication else 'success'),'Wrong native startup scenario')
    start,finish = row.get('read_started_ns'),row.get('read_finished_ns')
    outer_finish = native.get('outer_cleanup_finished_ns')
    need(all(type(t) is int and t > 0 for t in (start,finish,outer_finish))
         and outer_finish <= start <= finish,'Read occurred before native cleanup')
    original = base64.b64decode(row['original_base64'],validate=True) if row.get('original_base64') is not None else None
    captured = base64.b64decode(row['captured_base64'],validate=True) if row.get('captured_base64') is not None else None
    mutation = row.get('mutation_started_ns')
    if publication:
        need(original is None and row.get('original_sha256') is None and mutation is None,
             'Failed publication manufactured original bytes')
        need(result.get('journal_written') is False and bool(result.get('journal_error')),
             'Publication failure missing fallback')
    else:
        need(original is not None,'Original disk bytes missing')
        if original is not None:
            need(hashlib.sha256(original).hexdigest() == row.get('original_sha256'),'Original hash mismatch')
            need(canonical(decode(original)) == canonical(result),'Original disk journal differs from pipe')
        need(type(mutation) is int and start <= mutation <= finish,'Mutation phase outside read interval')
    verification = row.get('verification') or {}
    need(verification.get('accepted') is (fault=='valid'),'Wrong accept/reject classification')
    reason = ('CONTENT_MATCH' if fault=='valid' else 'JOURNAL_MISSING' if fault in ('missing','publication_failure')
              else 'INVALID_JSON' if fault=='truncated' else 'CONTENT_MISMATCH')
    need(verification.get('reason') == reason,'Wrong rejection reason')
    read_error = row.get('read_error')
    if fault in ('missing','publication_failure'):
        need(captured is None and verification.get('sha256') is None and verification.get('size') == 0,
             'Absent file has fabricated captured bytes')
        need(isinstance(read_error,dict) and read_error.get('type') == 'FileNotFoundError'
             and type(read_error.get('errno')) is int and read_error['errno'] > 0,'Missing real read error')
    else:
        need(captured is not None and read_error is None,'Missing captured bytes or unexpected read error')
        if captured is not None:
            need(verification.get('sha256') == hashlib.sha256(captured).hexdigest()
                 and type(verification.get('size')) is int and verification['size'] == len(captured),
                 'Captured hash/length mismatch')
            if fault=='truncated':
                need(original is not None and captured == original[:len(original)//2],'Truncation fixture differs')
                try:
                    decode(captured)
                except (ValueError,UnicodeError):
                    pass
                else:
                    need(False,'Truncated journal is valid JSON')
            else:
                actual = decode(captured)
                expected = json.loads(json.dumps(result))
                if fault == 'nonce': expected['nonce'] = '0'*32
                if fault == 'identity': expected['probe_pid'] += 1
                if fault == 'cleanup': expected['subject_cleanup']['confirmed'] = False
                if fault == 'authorization': expected['real_operations_authorized'] = True
                need(canonical(actual) == canonical(expected),'Captured content does not match declared fault')
                if fault == 'valid':
                    need(captured == original,'Valid disk bytes changed')
                else:
                    need(canonical(actual) != canonical(result),'Negative fixture unchanged')
    return errors


def audit(root,modes=(0,1)):
    files,failures,nonces,identities = [],[],set(),set()
    for mode in modes:
        names = []
        for path in sorted(Path(root).glob(f'a14_8_journal_evidence_O{mode}_*/*.json')):
            try:
                row = json.loads(path.read_bytes())
                errors = check(row,mode)
                names.append(row.get('test'))
                native = row.get('native') or {}
                nonce = native.get('nonce')
                identity = native.get('probe_identity') or {}
                pair = (identity.get('pid'),identity.get('creation_100ns'))
                if nonce in nonces or pair in identities:
                    errors.append('Native specimen reused')
                nonces.add(nonce)
                identities.add(pair)
            except (ValueError,TypeError,KeyError,AttributeError) as error:
                errors = ['Malformed evidence: '+repr(error)]
            failures.extend(str(path)+': '+error for error in errors)
            files.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if len(names)!=8 or set(names)!=set(SCENARIOS):
            failures.append(f'O{mode}: expected exactly eight fresh journal scenarios')
    return dict(accepted=not failures,files=files,records=len(files),failures=failures,
                scope='Post-cleanup journal content fidelity; no authentication or power-loss durability proof')


if __name__=='__main__':
    result = audit(sys.argv[1])
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
