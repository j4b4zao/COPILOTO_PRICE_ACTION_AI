"""Disposable descriptive probe; never stage this file."""
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median

from tools import prospective_microstructure_pa_book_temporal_duration_audit as duration

MANIFEST = Path('prospective_microstructure_conflict_10session_checkpoint_20260926.json')
EXPECTED = dict(samples=2746, simultaneous_directional_samples=356,
                aligned_samples=210, opposed_samples=146, total_runs=35,
                aligned_runs=17, opposed_runs=18)


def baseline():
    manifest = duration._read_json(MANIFEST)
    paths = [Path(item['path']) for item in manifest['sessions']]
    if manifest['session_count'] != 10 or len(paths) != 10:
        raise ValueError('frozen session identity failed')
    for item, path in zip(manifest['sessions'], paths):
        if duration._sha256(path) != item['sha256']:
            raise ValueError('frozen hash mismatch')
    report = duration.build_report(paths)
    if any(report['aggregate'][key] != value for key, value in EXPECTED.items()):
        raise ValueError('frozen numeric identity failed')
    return report


def stats(values):
    return dict(n=len(values), min=min(values) if values else None,
                median=median(values) if values else None,
                mean=mean(values) if values else None,
                max=max(values) if values else None)


def probe():
    report = baseline()
    rows = []
    for session in report['sessions']:
        for index, (previous, following) in enumerate(zip(session['runs'], session['runs'][1:]), 1):
            rows.append(dict(session=session['label'], previous_run=index, next_run=index+1,
                previous_relation=previous['relation'], next_relation=following['relation'],
                previous_pair=previous['pair'], next_pair=following['pair'],
                previous_end_index=previous['end_index'], next_start_index=following['start_index'],
                gap_samples=following['start_index']-previous['end_index']-1,
                previous_end_timestamp=previous['end_timestamp'], next_start_timestamp=following['start_timestamp'],
                gap_seconds=round((duration._parse_timestamp(following['start_timestamp'], following['start_index'])-
                    duration._parse_timestamp(previous['end_timestamp'], previous['end_index'])).total_seconds(), 6),
                previous_canonical_conflict_samples=previous['canonical_conflict_samples'],
                next_canonical_conflict_samples=following['canonical_conflict_samples']))
    expected = sum(max(len(s['runs'])-1, 0) for s in report['sessions'])
    if len(rows) != expected:
        raise ValueError('transition identity failed')
    relations = {}
    for previous in ('ALIGNED', 'OPPOSED'):
        for following in ('ALIGNED', 'OPPOSED'):
            subset = [r for r in rows if (r['previous_relation'], r['next_relation']) == (previous, following)]
            relations[previous+'->'+following] = dict(count=len(subset),
                gap_seconds=stats([r['gap_seconds'] for r in subset]),
                sessions=dict(Counter(r['session'] for r in subset)))
    return dict(identity=EXPECTED, session_count=10, total_transitions=len(rows),
        gap_definition='next_start_index - previous_end_index - 1; seconds = next_start_timestamp - previous_end_timestamp',
        relation_transitions=relations,
        pair_transitions=dict(Counter(r['previous_pair']+'->'+r['next_pair'] for r in rows)),
        gap_samples=stats([r['gap_samples'] for r in rows]),
        gap_sample_distribution=dict(sorted(Counter(r['gap_samples'] for r in rows).items())),
        gap_seconds=stats([r['gap_seconds'] for r in rows]), rows=rows,
        safety=duration.persistence._safety())


if __name__ == '__main__':
    result = probe()
    Path('pa_book_temporal_transitions_probe_20260929.txt').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}, indent=2))
