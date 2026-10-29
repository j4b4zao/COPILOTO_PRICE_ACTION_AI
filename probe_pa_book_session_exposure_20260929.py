"""Disposable check of observed windows and boundary-touching runs; no tuning."""
import json
from pathlib import Path

from tools import prospective_microstructure_pa_book_temporal_transition_audit as audit


def probe():
    report = audit.build_report()
    rows = []
    for s in report['sessions']:
        path = Path(s['raw_session']['path'])
        raw = audit.duration._read_json(path)['samples']
        seconds = (audit.duration._parse_timestamp(raw[-1]['timestamp'], len(raw)-1)
                   - audit.duration._parse_timestamp(raw[0]['timestamp'], 0)).total_seconds() if raw else None
        rows.append(dict(session=s['label'], samples=s['samples'], observed_window_seconds=seconds,
            simultaneous_samples=s['simultaneous_directional_samples'], runs=s['total_runs'],
            simultaneous_fraction_of_session_samples=s['simultaneous_directional_samples']/s['samples'] if s['samples'] else None,
            aligned_fraction_of_session_samples=s['aligned_samples']/s['samples'] if s['samples'] else None,
            opposed_fraction_of_session_samples=s['opposed_samples']/s['samples'] if s['samples'] else None,
            boundary_touching_runs=[dict(run=i, **r, touches_first_sample=r['start_index']==0,
                                        touches_last_sample=r['end_index']==s['samples']-1)
                                    for i,r in enumerate(s['runs'],1)
                                    if r['start_index']==0 or r['end_index']==s['samples']-1]))
    for path, digest in audit._frozen_entries():
        if audit.duration._sha256(path) != digest:
            raise ValueError('frozen input mutation')
    return dict(rows=rows, identity=audit.EXPECTED_BASELINE,
                total_boundary_touching_runs=sum(len(r['boundary_touching_runs']) for r in rows),
                definitions={'sample_fraction_denominator':'ALL_PROSPECTIVE_SAMPLES_IN_THE_SAME_SESSION',
                             'window_seconds':'LAST_RAW_TIMESTAMP_MINUS_FIRST_RAW_TIMESTAMP',
                             'boundary_flag':'TOUCHES_FIRST_OR_LAST_OBSERVED_SAMPLE_ONLY'},
                limits=['SAMPLE_FRACTION_IS_NOT_TIME_OCCUPANCY', 'BOUNDARY_TOUCH_DOES_NOT_PROVE_STATE_START_OR_END',
                        'NO_INFERENCE_ABOUT_UNOBSERVED_PERIODS', 'NO_COHORT_REDEFINITION'],
                safety=audit.duration.persistence._safety())


if __name__ == '__main__':
    result = probe()
    if result != probe():
        raise ValueError('reproducibility failed')
    Path('pa_book_session_exposure_probe_20260929.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result, indent=2))
