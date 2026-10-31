"""Audit retained real A12 bridge fixtures, distinct from natural observations."""
import hashlib
import json
from pathlib import Path
import sys

ROLES = {'owner','gate','bridge','worker'}


def check(row, mode):
    errors = []
    def need(ok, text):
        if not ok:
            errors.append(text)
    need(type(row.get('optimization')) is int and row['optimization'] == mode, 'Wrong optimization')
    need(row.get('negative_control') is True and row.get('observational') is False,
         'Strict negative fixture metadata changed')
    need(row.get('retained_bridge_fixture') is True, 'Retention not enabled')
    need(row.get('real_operations_authorized') is False and row.get('runtime_modified') is False,
         'Operational flags changed')
    before, after = row.get('handles_before_outer_cleanup', {}), row.get('handles_after_outer_cleanup', {})
    need(set(before) == ROLES and before.get('owner') is True and before.get('worker') is True and
         before.get('bridge') is False, 'Actual bridge survivor not observed')
    need(set(after) == ROLES and all(value is True for value in after.values()), 'Pinned handle still active')
    need(row.get('outer_cleanup_confirmed') is True and
         type(row.get('active_processes_after_cleanup')) is int and row['active_processes_after_cleanup'] == 0,
         'Cleanup not confirmed')
    identities = row.get('identities', {})
    need(set(identities) == ROLES, 'Pinned identities missing')
    for identity in identities.values():
        need(all(type(identity.get(k)) is int and identity[k] > 0 for k in ('pid','creation_100ns')),
             'Invalid pinned identity')
    markers = row.get('bridge_retention', {})
    need(set(markers) == {'ARMED','ACTIVE'}, 'Retention handshake incomplete')
    for phase in ('ARMED','ACTIVE'):
        marker = markers.get(phase, {})
        need(marker.get('schema') == 'A14_6_HELD_BRIDGE' and marker.get('phase') == phase,
             'Retention marker schema/phase mismatch')
        need(marker.get('pid') == identities.get('bridge', {}).get('pid'), 'Wrong bridge identity in marker')
        need(type(marker.get('optimization')) is int and marker['optimization'] == mode,
             'Wrong optimization in retention marker')
        need(marker.get('real_operations_authorized') is False, 'Marker authorization changed')
    armed, active = markers.get('ARMED',{}), markers.get('ACTIVE',{})
    need(isinstance(armed.get('specimen_id'),str) and bool(armed.get('specimen_id')) and
         armed.get('specimen_id') == active.get('specimen_id'), 'Retention specimens differ')
    need(type(armed.get('observed_ns')) is int and type(active.get('observed_ns')) is int and
         armed.get('observed_ns',0) <= active.get('observed_ns',-1), 'Retention timestamps invalid')
    return errors


def audit(root, logs=None, modes=(0,1)):
    errors, files = [], []
    seen_specimens, seen_identities = set(), set()
    for mode in modes:
        paths = sorted(Path(root).glob(f'a14_6_held_repeats_O{mode}_*/*.json'))
        expected = {f'a14_6_held_{order}_{i}' for order in ('worker_first','near_simultaneous') for i in (1,2,3)}
        labels = []
        for path in paths:
            row = json.loads(path.read_bytes())
            labels.append(row.get('label'))
            errors.extend(f'{path}: {failure}' for failure in check(row,mode))
            expected_label = f"a14_6_held_{row.get('order')}_{row.get('repetition')}"
            if row.get('label') != expected_label or row.get('total_repetitions') != 3:
                errors.append(f'{path}: Invalid repetition metadata')
            specimen = row.get('bridge_retention',{}).get('ARMED',{}).get('specimen_id')
            if specimen in seen_specimens:
                errors.append(f'{path}: Specimen reused')
            seen_specimens.add(specimen)
            for identity in row.get('identities',{}).values():
                pair = (identity.get('pid'),identity.get('creation_100ns'))
                if pair in seen_identities:
                    errors.append(f'{path}: Pinned identity reused')
                seen_identities.add(pair)
            files.append(dict(path=str(path),label=row.get('label'),optimization=mode,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if len(paths)!=6 or set(labels)!=expected:
            errors.append(f'Mode {mode}: expected six fresh repetitions')
        if logs:
            text = Path(logs[mode]).read_text(encoding='utf-8-sig')
            rows = [json.loads(line.split('=',1)[1]) for line in text.splitlines()
                    if line.startswith('A14_4_EXIT_ORDER_EVIDENCE=')]
            strict = [row for row in rows if row.get('label') in ('a14_4_worker_first','a14_4_close_succession')]
            natural = [row for row in rows if row.get('label','').startswith('a14_5_')]
            if len(strict)!=2:
                errors.append(f'Mode {mode}: missing strict A14.4 observations')
            for row in strict:
                errors.extend(f"Mode {mode}, {row.get('label')}: {failure}" for failure in check(row,mode))
            if len(natural)!=6 or any(row.get('retained_bridge_fixture') is not False or
                    row.get('observational') is not True or row.get('bridge_retention') != {} for row in natural):
                errors.append(f'Mode {mode}: natural A14.5 observational fixture changed')
    return dict(accepted=not errors,failures=errors,files=files,
                scope='Strict held bridges; natural A14.5 observations remain separate')


if __name__=='__main__':
    if len(sys.argv) not in (2,4):
        raise SystemExit('Usage: python auditar_a14_6_retencao.py root [normal.log optimized.log]')
    result = audit(sys.argv[1],sys.argv[2:] or None)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
