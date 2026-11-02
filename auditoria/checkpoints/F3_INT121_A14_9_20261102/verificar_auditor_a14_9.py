"""Corrupt recorded sharing evidence; separate from 213 project tests."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,'outputs')
import auditar_a14_9 as audit

root=Path('work/a14_9/work')
rows={r['scenario']:r for path in root.glob('a14_9_sharing_evidence_O0_*/*.json')
      for r in [json.loads(path.read_bytes())]}
if not audit.audit(root)['accepted']: raise RuntimeError('Original records rejected')
cases=[
    ('native_cleanup_false','transient_valid',lambda r:r['native']['outer_cleanup'].update(confirmed=False)),
    ('native_probe_alive','transient_valid',lambda r:r['native'].update(probe_signalled_after_cleanup=False)),
    ('read_before_cleanup','transient_valid',lambda r:r['timings'].update(original_read_started_ns=1)),
    ('fake_win32_sharing_code','transient_valid',lambda r:r.update(win32_denial=5)),
    ('boolean_win32_code','transient_valid',lambda r:r.update(win32_denial=True)),
    ('fake_python_denial','transient_valid',lambda r:r['reader']['attempts'][0]['error'].update(type='FileNotFoundError')),
    ('errno_lost','transient_valid',lambda r:r['reader']['attempts'][0]['error'].update(errno=0)),
    ('missing_label_conflated','missing',lambda r:r['reader'].update(status='JOURNAL_READ_DENIED')),
    ('denial_label_conflated','persistent',lambda r:r['reader'].update(status='JOURNAL_MISSING')),
    ('budget_changed','persistent',lambda r:r['reader'].update(deadline_ns=r['reader']['started_ns']+1)),
    ('deadline_not_reached','persistent',lambda r:r['reader'].update(finished_ns=r['reader']['started_ns'])),
    ('lock_released_early','persistent',lambda r:r['timings'].update(lock_release_started_ns=1)),
    ('success_before_release','transient_valid',lambda r:r['timings'].update(lock_release_finished_ns=10**30)),
    ('lock_left_open','persistent',lambda r:r.update(lock_closed=False)),
    ('close_error_lost','persistent',lambda r:r.update(lock_close_error='failed')),
    ('last_denial_lost','persistent',lambda r:r['reader'].update(error=None)),
    ('failure_manufactures_content','persistent',lambda r:r['reader'].update(verification={'accepted':True})),
    ('bytes_missing','transient_valid',lambda r:r.update(captured_base64=None)),
    ('corrupt_accepted','transient_corrupt',lambda r:r['reader']['verification'].update(accepted=True)),
    ('captured_hash_changed','transient_valid',lambda r:r['reader']['verification'].update(sha256='0'*64)),
    ('original_hash_changed','transient_valid',lambda r:r.update(original_sha256='0'*64)),
    ('strict_deadline_claim','persistent',lambda r:r['reader'].update(strict_deadline_guaranteed=True)),
    ('api_promoted','persistent',lambda r:r['reader'].update(production_api_changed=True)),
    ('real_operations_enabled','transient_valid',lambda r:r.update(real_operations_authorized=True)),
    ('authentication_claim','transient_valid',lambda r:r.update(authentication_tested=True)),
    ('durability_claim','transient_valid',lambda r:r.update(durability_tested=True)),
    ('wrong_optimization','transient_valid',lambda r:r.update(optimization=False)),
    ('observer_failed','transient_valid',lambda r:r.update(observer_error={'type':'RuntimeError'})),
]
checks=[]
for name,scenario,mutate in cases:
    row=copy.deepcopy(rows[scenario]); mutate(row)
    try: errors=audit.check(row,0)
    except (ValueError,TypeError,KeyError,AttributeError) as error: errors=[repr(error)]
    if not errors: raise RuntimeError('Corrupted record accepted: '+name)
    checks.append(dict(case=name,rejected=True))
Path('outputs/A14_9_VERIFICACAO_AUDITOR_20261102.json').write_text(json.dumps(dict(
    scope='Synthetic record mutations, separate from 213 project tests per mode',
    original_native_records_accepted=8,counterexamples=checks,accepted=True),indent=2),encoding='utf-8')
print(str(len(checks))+' corruptions rejected; eight native originals accepted')
