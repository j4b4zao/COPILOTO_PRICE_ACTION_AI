"""Offline replay of startup evidence; imports no project/operational code."""
import hashlib
import json
from pathlib import Path
import sys

SCENARIOS = {
    'test_injected_creation_failure_preserves_errno': 'create_failure',
    'test_real_invalid_cwd_preserves_winerror': 'invalid_cwd',
    'test_assignment_failure_never_releases_target': 'assign_failure',
    'test_gate_release_failure_never_releases_target': 'gate_failure',
    'test_target_crash_preserves_stderr': 'target_crash',
    'test_truncated_handshake_is_not_accepted': 'truncated_frame',
    'test_missing_handshake_times_out_after_entry': 'handshake_timeout',
    'test_journal_failure_preserves_fallback_after_cleanup': 'journal_failure',
    'test_successful_handshake_control_still_cleans': 'success',
}
LOCKS = {'orders_allowed','live_certified','flow_complete','f3_resolved',
         'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'}
PRESTART = {'create_failure','invalid_cwd','assign_failure','gate_failure','journal_failure'}
INJECTED = {'create_failure','assign_failure','gate_failure','journal_failure'}


def check(row, optimization):
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    def identity(value):
        return isinstance(value, dict) and all(type(value.get(k)) is int and value[k] > 0
                                               for k in ('pid','creation_100ns'))
    def key(value):
        return (value.get('pid'), value.get('creation_100ns'))
    def cleanup(value, nonempty):
        need(value.get('confirmed') is True and type(value.get('active_processes')) is int
             and value['active_processes'] == 0, 'Cleanup unconfirmed/active processes')
        need(value.get('live_io_threads') == [] and value.get('error') is None
             and value.get('tracker_error') is None, 'Cleanup errors/live threads')
        proofs = value.get('processes', [])
        need(not nonempty or bool(proofs), 'Missing native exit proofs')
        for proof in proofs:
            need(proof.get('exit_confirmed') is True, 'Unconfirmed native process exit')
            need((proof.get('proof') == 'PINNED_HANDLE_SIGNALLED' and identity(proof.get('identity')))
                 or (proof.get('proof') == 'OWN_JOB_EXIT_NOTIFICATION'
                     and type(proof.get('pid')) is int and proof['pid'] > 0), 'Invalid proof identity/type')
        return proofs
    mode = SCENARIOS.get(row.get('test'))
    need(mode is not None and row.get('mode') == mode, 'Unexpected scenario')
    result = row.get('result') or {}
    nonce = row.get('nonce')
    need(isinstance(nonce,str) and len(nonce) == 32 and all(c in '0123456789abcdef' for c in nonce), 'Invalid nonce')
    for record in (row,result):
        need(type(record.get('optimization')) is int and record['optimization'] == optimization, 'Wrong optimization')
        need(record.get('f3') == 'OPEN' and record.get('offline') is True
             and record.get('simulation_only') is True and record.get('real_operations_authorized') is False
             and record.get('runtime_modified') is False, 'Operational restrictions changed')
        need(record.get('nonce') == nonce and record.get('mode') == mode, 'Cross-record identity mismatch')
    need(set(row.get('operational_locks',{})) == LOCKS
         and all(v is False for v in row.get('operational_locks',{}).values()), 'Missing/enabled operational lock')
    need(result.get('schema') == 'A14_7_STARTUP_RECORD', 'Wrong record schema')
    need(result.get('subject_cleanup_scope') == 'INNER_JOB_AND_DIRECT_LAUNCH_PROCESS_ONLY'
         and result.get('full_subtree_exit_requires_outer_safety_proof') is True
         and result.get('constructor_evidence_is_private') is True
         and result.get('production_api_changed') is False, 'Private proof scope promoted')
    need(row.get('observer_error') is None and row.get('outer_cleanup_error') is None
         and result.get('subject_cleanup_error') is None, 'Unexpected observer/cleanup error')
    need(result.get('subject_job_handle_closed') is True and result.get('subject_tracker_closed') is True,
         'Subject handles not closed')
    outer = cleanup(row.get('outer_cleanup') or {}, True)
    cleanup(result.get('subject_cleanup') or {}, False)
    probe = row.get('probe_identity') or {}
    need(identity(probe) and probe.get('pid') == result.get('probe_pid')
         and row.get('probe_signalled_after_cleanup') is True, 'Probe identity/exit missing')
    need(any(p.get('identity') == probe for p in outer), 'Probe absent from pinned outer proof')
    direct = result.get('direct_processes', [])
    need(len(direct) == (0 if mode in {'create_failure','invalid_cwd','journal_failure'} else 1), 'Wrong creation count')
    for process in direct:
        ident = process.get('identity') or {}
        need(identity(ident) and process.get('exit_confirmed') is True
             and process.get('proof') == 'PINNED_HANDLE_SIGNALLED', 'Direct launch lacks pinned exit proof')
        need(any((p.get('identity') and key(p['identity']) == key(ident))
                 or (p.get('proof') == 'OWN_JOB_EXIT_NOTIFICATION' and p.get('pid') == ident.get('pid'))
                 for p in outer), 'Direct process absent from outer subtree proof')
    times = [result.get('started_ns'),result.get('cleanup_confirmation_started_ns'),
             result.get('cleanup_confirmation_finished_ns'),result.get('journal_attempt_started_ns'),
             row.get('outer_cleanup_started_ns'),row.get('outer_cleanup_finished_ns')]
    need(all(type(t) is int and t > 0 for t in times)
         and all(a <= b for a,b in zip(times,times[1:])), 'Cleanup/journal temporal order invalid')
    entry = result.get('target_entry')
    need((entry is None) == (mode in PRESTART), 'Target entry violates startup barrier')
    if entry:
        need(entry.get('nonce') == nonce and type(entry.get('optimization')) is int and entry['optimization'] == optimization
             and type(entry.get('pid')) is int and entry['pid'] > 0, 'Invalid target marker')
        need(any(p.get('identity',{}).get('pid') == entry.get('pid') or
                 (p.get('proof') == 'OWN_JOB_EXIT_NOTIFICATION' and p.get('pid') == entry.get('pid'))
                 for p in outer), 'Target missing from outer subtree proof')
    need(result.get('controlled_injection') is (mode in INJECTED), 'Real/injected error misclassified')
    need(result.get('subject_constructor_completed') is (mode not in PRESTART), 'Wrong constructor state')
    need(result.get('subject_assigned') is (mode not in {'create_failure','invalid_cwd','assign_failure','journal_failure'}),
         'Wrong Job assignment state')
    error = result.get('observed_error')
    primary = result.get('primary_errors', [])
    frame = result.get('received_frame')
    if mode == 'success':
        need(error is None and primary == [], 'Control unexpectedly failed')
        frame = frame or {}
        need(frame.get('schema') == 'A14_7_READY' and frame.get('nonce') == nonce
             and type(frame.get('optimization')) is int and frame['optimization'] == optimization and entry is not None
             and frame.get('pid') == entry.get('pid'), 'Invalid control handshake')
    else:
        error = error or {}
        need(bool(error) and frame is None, 'Failure accepted as handshake')
        need(type(error.get('observed_ns')) is int and error['observed_ns'] >= result.get('started_ns',0)
             and error['observed_ns'] <= result.get('cleanup_confirmation_started_ns',0), 'Failure timestamp outside startup')
        need(error.get('stage') == ('construct_peer' if mode in PRESTART else 'recv_handshake'), 'Wrong failure stage')
        if mode in PRESTART:
            need(len(primary) == 1, 'Missing primary constructor error')
            first = primary[0] if primary else {}
            need(first.get('stage') == ('assign_job' if mode == 'assign_failure' else
                 'release_gate' if mode == 'gate_failure' else 'create_process'), 'Wrong primary error stage')
            need(all(first.get(k) == error.get(k) for k in ('type','errno','winerror','message')), 'Original error lost')
            need(type(first.get('observed_ns')) is int and first['observed_ns'] <= error.get('observed_ns',0),
                 'Primary error occurred after observed error')
            if mode == 'invalid_cwd':
                need(error.get('is_os_error') is True and type(error.get('winerror')) is int
                     and error['winerror'] > 0, 'Real Windows error missing')
            else:
                need(error.get('type') == ('BrokenPipeError' if mode == 'gate_failure' else 'PermissionError')
                     and error.get('errno') == (32 if mode == 'gate_failure' else 13)
                     and error.get('winerror') is None and error.get('is_os_error') is True, 'Injected errno altered')
        else:
            need(primary == [], 'Unexpected injected primary error')
            need(error.get('type') == {'target_crash':'EOFError','truncated_frame':'RuntimeError',
                                      'handshake_timeout':'TimeoutError'}.get(mode), 'Wrong handshake error')
            if mode == 'target_crash':
                need('A14_7_TARGET_STARTUP_CRASH' in result.get('subject_stderr',''), 'Crash stderr lost')
            if mode == 'truncated_frame':
                need(error.get('message') == 'Truncated stdout frame'
                     and 'A14_7_TARGET_TRUNCATED_FRAME' in result.get('subject_stderr',''), 'Truncated frame diagnostic lost')
    journal = result.get('journal_error')
    if mode == 'journal_failure':
        journal = journal or {}
        need(result.get('journal_written') is False and journal.get('is_os_error') is True
             and journal.get('stage') == 'publish_after_cleanup'
             and type(journal.get('errno')) is int and journal['errno'] > 0
             and type(journal.get('observed_ns')) is int
             and journal['observed_ns'] >= result.get('journal_attempt_started_ns',0)
             and journal['observed_ns'] <= row.get('outer_cleanup_started_ns',0)
             and 'A14_7_JOURNAL_PUBLISH_FAILED' in row.get('outer_stderr',''), 'Journal fallback diagnostic lost')
    else:
        need(result.get('journal_written') is True and journal is None, 'Unexpected journal failure')
    return errors


def audit(root, modes=(0,1)):
    records, failures, seen, identities = [], [], set(), set()
    for mode in modes:
        files = sorted(Path(root).glob(f'a14_7_startup_evidence_O{mode}_*/*.json'))
        names = []
        for path in files:
            try:
                row = json.loads(path.read_bytes())
                errors = check(row,mode)
                names.append(row.get('test'))
                nonce = row.get('nonce')
                if nonce in seen:
                    errors.append('Reused specimen nonce')
                seen.add(nonce)
                probe = row.get('probe_identity') or {}
                pair = (probe.get('pid'),probe.get('creation_100ns'))
                if pair in identities:
                    errors.append('Reused pinned probe identity')
                identities.add(pair)
            except (ValueError,TypeError,KeyError,AttributeError) as error:
                errors = ['Malformed evidence: '+repr(error)]
            records.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            failures.extend(str(path)+': '+error for error in errors)
        if len(names) != len(SCENARIOS) or set(names) != set(SCENARIOS):
            failures.append(f'O{mode}: expected exactly nine distinct startup scenarios')
    return dict(accepted=not failures,records=len(records),files=records,failures=failures,
                scope='PRIVATE_STARTUP_AND_OUTER_SAFETY_JOB_ONLY',production_api_changed=False)


if __name__ == '__main__':
    result = audit(sys.argv[1])
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
