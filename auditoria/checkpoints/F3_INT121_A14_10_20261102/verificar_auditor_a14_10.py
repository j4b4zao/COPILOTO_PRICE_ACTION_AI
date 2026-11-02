"""Adversarial observer evidence replay, separate from 216 project tests."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,'outputs')
import auditar_a14_10 as audit

root=Path('work/a14_10/work')
rows={r['scenario']:r for path in root.glob('a14_10_observer_evidence_O0_*/*.json')
      for r in [json.loads(path.read_bytes())]}
if not audit.audit(root)['accepted']: raise RuntimeError('Original records rejected')
cases=[
    ('native_cleanup_false','fail_before_release',lambda r:r['native']['outer_cleanup'].update(confirmed=False)),
    ('native_probe_alive','fail_before_release',lambda r:r['native'].update(probe_signalled_after_cleanup=False)),
    ('post_close_bytes_changed','fail_before_release',lambda r:r.update(post_close_base64='e30=')),
    ('hash_changed','fail_before_release',lambda r:r.update(sha256='0'*64)),
    ('error_lost','fail_before_release',lambda r:r.update(callback_error=None)),
    ('error_message_changed','fail_after_release',lambda r:r['callback_error'].update(message='another')),
    ('missing_callback','fail_before_release',lambda r:r.update(callbacks=[])),
    ('denial_type_changed','fail_before_release',lambda r:r['callbacks'][0]['error'].update(type='FileNotFoundError')),
    ('denial_errno_lost','fail_before_release',lambda r:r['callbacks'][0]['error'].update(errno=0)),
    ('fake_win32_error','fail_before_release',lambda r:r.update(win32_denial=5)),
    ('lock_left_open','fail_before_release',lambda r:r.update(lock_closed=False)),
    ('close_failed','fail_before_release',lambda r:r.update(close_error='failed')),
    ('finally_before_reader','fail_before_release',lambda r:r['timings'].update(finally_started_ns=1)),
    ('premature_release','fail_before_release',lambda r:r['timings'].update(release_started_ns=1)),
    ('release_after_read','fail_after_release',lambda r:r['timings'].update(release_finished_ns=10**30)),
    ('late_read_accepted','over_budget',lambda r:r['reader'].update(status='CONTENT_MATCH')),
    ('late_attempt_added','over_budget',lambda r:r['reader']['attempts'].append(copy.deepcopy(r['reader']['attempts'][0]))),
    ('verification_manufactured','over_budget',lambda r:r['reader'].update(verification={'accepted':True})),
    ('last_denial_lost','over_budget',lambda r:r['reader'].update(error=None)),
    ('budget_changed','over_budget',lambda r:r['reader'].update(deadline_ns=r['reader']['started_ns']+1)),
    ('unexpected_callback_error','over_budget',lambda r:r.update(callback_error={'type':'RuntimeError'})),
    ('scope_strict_deadline','over_budget',lambda r:r.update(strict_deadline_guaranteed=True)),
    ('real_operations_enabled','over_budget',lambda r:r.update(real_operations_authorized=True)),
    ('uncontrolled_fault','fail_before_release',lambda r:r.update(fault_is_controlled=False)),
    ('observer_failed','fail_after_release',lambda r:r.update(observer_error={'type':'AssertionError'})),
    ('boolean_mode','fail_before_release',lambda r:r.update(optimization=False)),
]
checks=[]
for name,scenario,mutate in cases:
    row=copy.deepcopy(rows[scenario]); mutate(row)
    try: errors=audit.check(row,0)
    except (ValueError,TypeError,KeyError,AttributeError) as error: errors=[repr(error)]
    if not errors: raise RuntimeError('Corrupted evidence accepted: '+name)
    checks.append(dict(case=name,rejected=True))
Path('outputs/A14_10_VERIFICACAO_AUDITOR_20261102.json').write_text(json.dumps(dict(
    scope='Synthetic evidence corruptions, separate from 216 project tests per mode',
    original_native_records_accepted=6,counterexamples=checks,accepted=True),indent=2),encoding='utf-8')
print(str(len(checks))+' corruptions rejected; six original native records accepted')
