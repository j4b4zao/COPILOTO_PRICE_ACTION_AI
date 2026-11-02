"""Adversarial replay checks, separate from project unittest counts."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0,'outputs')
import auditar_a14_8 as auditor
spec = importlib.util.spec_from_file_location('candidate_journal','work/a14_8/src/f3_int121_a14_8_journal.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
root = Path('work/a14_8/work')
rows = {r['fault']:r for path in root.glob('a14_8_journal_evidence_O0_*/*.json')
        for r in [json.loads(path.read_bytes())]}
if not auditor.audit(root)['accepted']:
    raise RuntimeError('Native baseline rejected')
cases = [
    ('native_cleanup_false','valid',lambda r:r['native']['outer_cleanup'].update(confirmed=False)),
    ('native_probe_alive','valid',lambda r:r['native'].update(probe_signalled_after_cleanup=False)),
    ('native_proof_scope_promoted','valid',lambda r:r['native']['result'].update(full_subtree_exit_requires_outer_safety_proof=False)),
    ('read_before_cleanup','valid',lambda r:r.update(read_started_ns=1)),
    ('mutation_before_read','nonce',lambda r:r.update(mutation_started_ns=1)),
    ('read_finish_before_start','valid',lambda r:r.update(read_finished_ns=1)),
    ('original_hash_altered','valid',lambda r:r.update(original_sha256='0'*64)),
    ('original_missing','valid',lambda r:r.update(original_base64=None)),
    ('captured_hash_altered','valid',lambda r:r['verification'].update(sha256='0'*64)),
    ('captured_length_altered','valid',lambda r:r['verification'].update(size=0)),
    ('negative_accepted','nonce',lambda r:r['verification'].update(accepted=True)),
    ('wrong_reason','nonce',lambda r:r['verification'].update(reason='INVALID_JSON')),
    ('negative_not_mutated','nonce',lambda r:r.update(captured_base64=r['original_base64'])),
    ('unexpected_read_error','valid',lambda r:r.update(read_error={'type':'PermissionError'})),
    ('missing_read_error','missing',lambda r:r.update(read_error=None)),
    ('fallback_error_lost','publication_failure',lambda r:r['native']['result'].update(journal_error=None)),
    ('fallback_stderr_lost','publication_failure',lambda r:r['native'].update(outer_stderr='')),
    ('disk_absence_fabricated','publication_failure',lambda r:r['verification'].update(size=10)),
    ('real_operations_enabled','valid',lambda r:r.update(real_operations_authorized=True)),
    ('power_loss_claim','valid',lambda r:r.update(durability_tested=True)),
    ('authentication_claim','valid',lambda r:r.update(authentication_tested=True)),
    ('wrong_optimization','valid',lambda r:r.update(optimization=False)),
    ('observer_failed','valid',lambda r:r.update(observer_error={'type':'RuntimeError'})),
]
checks=[]
for name,fault,mutate in cases:
    row=copy.deepcopy(rows[fault])
    mutate(row)
    try:
        errors=auditor.check(row,0)
    except (ValueError,TypeError,KeyError,AttributeError) as error:
        errors=[repr(error)]
    if not errors:
        raise RuntimeError('Adulteration accepted: '+name)
    checks.append(dict(case=name,rejected=True))
expected=rows['valid']['native']['result']
original=base64.b64decode(rows['valid']['original_base64'])
if not candidate.compare(original,expected)['accepted']:
    raise RuntimeError('Candidate rejects original')
wrong_bool=copy.deepcopy(expected)
wrong_bool['optimization']=False
scope=copy.deepcopy(expected)
scope['real_operations_authorized']=True
strict_cases=[
    ('duplicate_json_key',b'{"nonce":"x",'+original[1:],expected),
    ('nonfinite_json',b'{"extra":NaN,'+original[1:],expected),
    ('boolean_integer_confusion',json.dumps(wrong_bool).encode(),expected),
    ('malformed_bytes',b'\xff\xff',expected),
    ('scope_invalid_even_if_pipe_matches',json.dumps(scope).encode(),scope),
]
for name,raw,pipe in strict_cases:
    if candidate.compare(raw,pipe)['accepted']:
        raise RuntimeError('Strict candidate input accepted: '+name)
    checks.append(dict(case=name,rejected=True,scope='candidate comparer'))
Path('outputs/A14_8_VERIFICACAO_AUDITOR_20261102.json').write_text(json.dumps(dict(
    scope='Synthetic counterexamples; not included in 209 project tests per mode',
    original_native_records_accepted=16,counterexamples=checks,accepted=True),indent=2),encoding='utf-8')
print(str(len(checks))+' counterexamples rejected; 16 native originals accepted')
