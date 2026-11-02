"""Replay A14.6 evidence without executing specimens or importing trading code.

Usage: python auditar_a14_6.py evidence_root
"""
import hashlib
import json
from pathlib import Path
import sys

EXPECTED = {
    'test_negative_owner_first_retains_descendant': ('owner_first', True, None),
    'test_negative_worker_first_retains_descendant': ('worker_first', True, None),
    'test_negative_close_succession_retains_descendant': ('near_succession', True, None),
    'test_positive_inner_job_kills_retained_descendant': ('owner_first', False, None),
    'test_missing_handshake_is_failure_and_cleans': ('owner_first', True, 'missing_handshake'),
    'test_injected_observer_failure_still_cleans': ('owner_first', True, 'observer_failure'),
}
ROLES = {'owner', 'host', 'worker', 'held'}
LOCKS = {'orders_allowed','live_certified','flow_complete','f3_resolved',
         'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'}


def audit_record(row, mode):
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    name = row.get('test')
    require(name in EXPECTED, 'Unexpected scenario')
    if name not in EXPECTED:
        return errors
    order, negative, fault = EXPECTED[name]
    require(row.get('order') == order and row.get('negative_control') is negative and row.get('fault') == fault,
            'Scenario metadata mismatch')
    require(type(row.get('optimization')) is int and row['optimization'] == mode, 'Wrong optimization mode')
    require(row.get('f3') == 'OPEN' and row.get('offline') is True and row.get('simulation_only') is True,
            'Offline/F3 restrictions absent')
    require(row.get('real_operations_authorized') is False and row.get('runtime_modified') is False,
            'Operational authorization changed')
    require(row.get('synthetic_barrier_only') is True and row.get('sqlite_durability_tested') is False,
            'Synthetic scope changed')
    locks = row.get('operational_locks', {})
    require(set(locks) == LOCKS and all(v is False for v in locks.values()), 'Operational lock missing or enabled')
    identities = row.get('identities', {})
    require(set(identities) == ROLES, 'Incomplete retained identities')
    for identity in identities.values():
        require(all(type(identity.get(key)) is int and identity[key] > 0 for key in ('pid','creation_100ns')),
                'Invalid retained process identity')
    pairs = [(v.get('pid'), v.get('creation_100ns')) for v in identities.values()]
    require(len(pairs) == len(set(pairs)), 'Duplicate identity within specimen')
    cleanup = row.get('cleanup') or {}
    require(row.get('cleanup_error') is None and cleanup.get('confirmed') is True, 'Cleanup not confirmed')
    require(type(cleanup.get('active_processes')) is int and cleanup['active_processes'] == 0,
            'Processes remain after cleanup')
    require(cleanup.get('live_io_threads') == [], 'I/O threads remain')
    proofs = cleanup.get('processes', [])
    require(bool(proofs) and all(p.get('exit_confirmed') is True and
            p.get('proof') in ('PINNED_HANDLE_SIGNALLED','OWN_JOB_EXIT_NOTIFICATION') for p in proofs),
            'Missing native exit proof')
    after = row.get('after_outer_cleanup', {})
    require(set(after) == ROLES and all(v is True for v in after.values()), 'Final retained handle still active')
    snapshots = row.get('snapshots', {})
    initial = snapshots.get('initial_pinned', {}).get('signalled', {})
    require(set(initial) == ROLES and all(v is False for v in initial.values()), 'Initial specimen not fully alive')
    start, finish = row.get('outer_cleanup_started_ns'), row.get('outer_cleanup_finished_ns')
    require(type(start) is int and type(finish) is int and 0 < start <= finish, 'Invalid cleanup timing')
    observed = [value.get('observed_ns') for value in snapshots.values()]
    if all(type(t) is int for t in observed) and type(start) is int:
        require(observed == sorted(observed) and all(0 < t <= start for t in observed), 'Snapshot ordering invalid')
    else:
        errors.append('Snapshot timing absent')
    nonce = row.get('nonce')
    require(isinstance(nonce, str) and len(nonce) == 32, 'Specimen nonce absent')
    diagnostics = row.get('diagnostics', {})
    for role, filename in [('owner','owner.json'), ('host','host.json'),
                           ('worker','worker-ready.json'), ('held','held-ready.json')]:
        marker = diagnostics.get(filename, {})
        require(marker.get('nonce') == nonce and marker.get('pid') == identities.get(role, {}).get('pid'),
                'Marker/retained identity mismatch: ' + role)
        require(type(marker.get('optimization')) is int and marker['optimization'] == mode,
                'Marker optimization mismatch: ' + role)
    owner = diagnostics.get('owner.json', {})
    require(type(owner.get('inner_job_limit_flags')) is int and
            owner.get('inner_job_limit_flags') == (0 if negative else 0x2000) and
            owner.get('negative_control') is negative, 'Wrong private inner Job mode')
    failure = row.get('error')
    before, handshake = row.get('before_outer_cleanup'), row.get('handshake')
    if fault == 'missing_handshake':
        require(isinstance(failure, dict) and failure.get('type') == 'TimeoutError' and
                failure.get('message') == 'A14_6_HANDSHAKE_TIMEOUT' and failure.get('stage') == 'handshake',
                'Expected handshake failure not preserved')
        require(handshake is None and before is None, 'Failed handshake falsely reported as successful observation')
    else:
        require(isinstance(handshake, dict) and handshake.get('nonce') == nonce and
                handshake.get('pid') == identities.get('held', {}).get('pid') and handshake.get('state') == 'HELD',
                'Held descendant handshake absent')
        ready = snapshots.get('handshake_confirmed', {}).get('signalled', {})
        require(ready.get('held') is False, 'Held descendant not alive at handshake')
        require(isinstance(before, dict) and set(before) == ROLES, 'Final observation before cleanup missing')
        if isinstance(before, dict):
            require(before == snapshots.get('confirmed_before_outer_cleanup', {}).get('signalled'),
                    'Confirmed observation differs from snapshot')
            if negative:
                require(before.get('owner') is True and before.get('worker') is True and
                        before.get('host') is False and before.get('held') is False,
                        'Negative retained survivor not observed after target exits')
            else:
                require(all(v is True for v in before.values()), 'Positive containment only established by outer cleanup')
        if fault == 'observer_failure':
            require(isinstance(failure, dict) and failure.get('type') == 'RuntimeError' and
                    failure.get('message') == 'A14_6_INJECTED_OBSERVER_FAILURE' and
                    failure.get('stage') == 'confirmed_before_outer_cleanup',
                    'Injected observer failure not preserved')
        else:
            require(failure is None, 'Unexpected observer failure')
    return errors


def audit_barriers(root, modes=(0, 1)):
    files, errors = [], []
    seen_nonces, seen_identities = set(), set()
    for mode in modes:
        paths = sorted(Path(root).glob(f'a14_6_evidence_O{mode}_*/*.json'))
        names = []
        for path in paths:
            row = json.loads(path.read_bytes())
            names.append(row.get('test'))
            for error in audit_record(row, mode):
                errors.append(f'{path}: {error}')
            nonce = row.get('nonce')
            if nonce in seen_nonces:
                errors.append(f'{path}: Specimen nonce reused')
            seen_nonces.add(nonce)
            for identity in row.get('identities', {}).values():
                pair = (identity.get('pid'), identity.get('creation_100ns'))
                if pair in seen_identities:
                    errors.append(f'{path}: Retained process identity reused')
                seen_identities.add(pair)
            files.append(dict(path=str(path), test=row.get('test'), optimization=mode,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if len(paths) != 6 or set(names) != set(EXPECTED):
            errors.append(f'Mode {mode}: expected exactly six distinct scenarios')
    return dict(accepted=not errors, failures=errors, files=files,
                scope='Synthetic Windows Jobs/barrier records; not production certification')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    result = audit_barriers(sys.argv[1])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
