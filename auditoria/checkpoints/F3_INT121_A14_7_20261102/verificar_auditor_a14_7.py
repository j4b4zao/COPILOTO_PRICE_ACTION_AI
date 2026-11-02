"""Mutate saved native evidence; these checks are not project test counts."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile

spec = importlib.util.spec_from_file_location('startup_audit','outputs/auditar_a14_7.py')
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)
root = Path('work/a14_7/work')
rows = {row['mode']:row for path in root.glob('a14_7_startup_evidence_O0_*/*.json')
        for row in [json.loads(path.read_bytes())]}
baseline = auditor.audit(root)
if not baseline['accepted']:
    raise RuntimeError(baseline)
cases = [
    ('cleanup_false','success',lambda x:x['outer_cleanup'].update(confirmed=False)),
    ('active_process','success',lambda x:x['outer_cleanup'].update(active_processes=1)),
    ('live_thread','success',lambda x:x['outer_cleanup'].update(live_io_threads=['reader'])),
    ('missing_probe_identity','success',lambda x:x.update(probe_identity={})),
    ('probe_not_signalled','success',lambda x:x.update(probe_signalled_after_cleanup=False)),
    ('subtree_proof_missing','assign_failure',lambda x:x['outer_cleanup'].update(processes=[])),
    ('inner_proof_promoted','assign_failure',lambda x:x['result'].update(full_subtree_exit_requires_outer_safety_proof=False)),
    ('changed_api','success',lambda x:x['result'].update(production_api_changed=True)),
    ('real_trading_enabled','success',lambda x:x.update(real_operations_authorized=True)),
    ('lock_enabled','success',lambda x:x['operational_locks'].update(orders_allowed=True)),
    ('lock_removed','success',lambda x:x['operational_locks'].pop('live_certified')),
    ('wrong_nonce','success',lambda x:x['result'].update(nonce='a'*32)),
    ('wrong_frame_pid','success',lambda x:x['result']['received_frame'].update(pid=1)),
    ('boolean_frame_mode','success',lambda x:x['result']['received_frame'].update(optimization=False)),
    ('fake_entry','create_failure',lambda x:x['result'].update(target_entry={'pid':1})),
    ('lost_errno','create_failure',lambda x:x['result']['observed_error'].update(errno=0)),
    ('fake_winerror','create_failure',lambda x:x['result']['observed_error'].update(winerror=5)),
    ('real_error_marked_injected','invalid_cwd',lambda x:x['result'].update(controlled_injection=True)),
    ('lost_real_winerror','invalid_cwd',lambda x:x['result']['observed_error'].update(winerror=None)),
    ('assignment_lied','assign_failure',lambda x:x['result'].update(subject_assigned=True)),
    ('stderr_lost','target_crash',lambda x:x['result'].update(subject_stderr='')),
    ('truncated_frame_accepted','truncated_frame',lambda x:x['result'].update(received_frame={})),
    ('timeout_wrong_stage','handshake_timeout',lambda x:x['result']['observed_error'].update(stage='construct_peer')),
    ('journal_marked_written','journal_failure',lambda x:x['result'].update(journal_written=True)),
    ('fallback_stderr_lost','journal_failure',lambda x:x.update(outer_stderr='')),
    ('journal_before_cleanup','journal_failure',lambda x:x['result'].update(journal_attempt_started_ns=1)),
    ('primary_error_reordered','gate_failure',lambda x:x['result']['primary_errors'][0].update(observed_ns=10**30)),
    ('outer_cleanup_before_journal','success',lambda x:x.update(outer_cleanup_started_ns=1)),
]
checks = []
for name,mode,mutate in cases:
    row = copy.deepcopy(rows[mode])
    mutate(row)
    errors = auditor.check(row,0)
    if not errors:
        raise RuntimeError('Corrupted evidence accepted: '+name)
    checks.append(dict(case=name,rejected=True,reasons=errors))
with tempfile.TemporaryDirectory(dir='work',prefix='a14_7_auditor_') as directory:
    target = Path(directory)/'a14_7_startup_evidence_O0_fake'
    target.mkdir()
    for name,row in rows.items():
        (target/(name+'.json')).write_text(json.dumps(row),encoding='utf-8')
    for name,change in (
        ('missing_scenario',lambda: (target/'success.json').unlink()),
        ('malformed_record',lambda: (target/'success.json').write_text('null',encoding='utf-8')),
    ):
        change()
        result = auditor.audit(directory,modes=(0,))
        if result['accepted']:
            raise RuntimeError(name+' accepted')
        checks.append(dict(case=name,rejected=True))
result = dict(scope='Synthetic adversarial checks, separate from 201 project tests per mode',
              original_records_accepted=18,counterexamples=checks,accepted=True)
Path('outputs/A14_7_VERIFICACAO_AUDITOR_20261102.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(str(len(checks))+' corruptions rejected; 18 original records accepted')
