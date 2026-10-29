"""Disposable sequential probes A-D; descriptive only, never stage."""
import json
from collections import Counter
from pathlib import Path

from tools import prospective_microstructure_pa_book_temporal_transition_audit as audit


def concentration(counts):
    total = sum(counts.values())
    ordered = sorted(counts.values(), reverse=True)
    return dict(total=total, counts=counts,
                shares={s: n / total if total else None for s, n in counts.items()},
                top_one_share=ordered[0] / total if total else None,
                top_two_share=sum(ordered[:2]) / total if total else None,
                sum_squared_shares=sum((n / total)**2 for n in counts.values()) if total else None)


def probe():
    report = audit.build_report()
    sessions = report['sessions']
    runs = [{**r, 'session': s['label'], 'run': i}
            for s in sessions for i, r in enumerate(s['runs'], 1)]
    transitions = [t for s in sessions for t in s['transitions']]
    # A: no arbitrary short/long cutoffs; retain actual gaps and session omissions.
    gaps = {
        'pooled': audit._summary(transitions),
        'by_session': {s['label']: audit._summary(s['transitions']) for s in sessions},
        'omit_one_session_descriptive_sensitivity': {
            s['label']: audit._summary([t for t in transitions if t['session'] != s['label']])
            for s in sessions},
        'largest_gap': max(transitions, key=lambda t: t['gap_seconds']),
        'zero_gap_samples_count': sum(t['gap_samples'] == 0 for t in transitions),
        'positive_gap_samples_count': sum(t['gap_samples'] > 0 for t in transitions),
    }
    # B: all ten sessions remain in every denominator; no cohort selection.
    measures = ('simultaneous_directional_samples', 'total_runs', 'aligned_samples',
                'opposed_samples', 'aligned_runs', 'opposed_runs')
    concentrations = {m: concentration({s['label']: s[m] for s in sessions}) for m in measures}
    # C: distinguish incoming/outgoing transition gaps, no double-counted pooled gap.
    pairs = {}
    for pair in audit.PAIRS:
        subset = [r for r in runs if r['pair'] == pair]
        pairs[pair] = dict(samples=sum(r['length'] for r in subset), runs=len(subset),
            run_lengths=audit._stats([r['length'] for r in subset]),
            observed_duration_seconds=audit._stats([r['observed_duration_seconds'] for r in subset]),
            total_observed_duration_seconds=round(sum(r['observed_duration_seconds'] for r in subset), 6),
            sessions=dict(Counter(r['session'] for r in subset)),
            incoming_gap=audit._summary([t for t in transitions if t['next_pair'] == pair]),
            outgoing_gap=audit._summary([t for t in transitions if t['previous_pair'] == pair]))
    # D: canonical conflict remains the RC1 conflict_count > 0 attribute.
    overlap = {}
    for relation in audit.RELATIONS:
        subset = [r for r in runs if r['relation'] == relation]
        rows = [{**r, 'conflict_sample_fraction': r['canonical_conflict_samples'] / r['length'],
                 'overlap': ('NONE' if r['canonical_conflict_samples'] == 0 else
                             'FULL' if r['canonical_conflict_samples'] == r['length'] else 'PARTIAL')}
                for r in subset]
        overlap[relation] = dict(run_counts=dict(Counter(r['overlap'] for r in rows)),
            conflict_samples=sum(r['canonical_conflict_samples'] for r in rows),
            samples=sum(r['length'] for r in rows), rows=rows)
    if sum(p['samples'] for p in pairs.values()) != 356 or sum(p['runs'] for p in pairs.values()) != 35:
        raise ValueError('pair identity failed')
    if sum(c['samples'] for c in overlap.values()) != 356:
        raise ValueError('overlap identity failed')
    if sum(s['total_transitions'] for s in gaps['by_session'].values()) != 28:
        raise ValueError('gap identity failed')
    for relation in audit.RELATIONS:
        key = relation.lower()
        if overlap[relation]['conflict_samples'] != report['aggregate'][key + '_canonical_conflict_samples']:
            raise ValueError('canonical attribute identity failed')
    return dict(identity=audit.EXPECTED_BASELINE, session_count=10,
                A_transition_gap=gaps, B_session_concentration=concentrations,
                C_pair_persistence=pairs, D_conflict_overlap=overlap,
                interpretation='DESCRIPTIVE_ONLY', safety=audit.duration.persistence._safety(),
                limitations=['UNEQUAL_OBSERVED_SESSION_WINDOWS', 'NO_OPERATIONAL_THRESHOLDS',
                             'NO_PREDICTIVE_OR_CAUSAL_CLAIMS', 'NO_RUN_EPISODE_EQUIVALENCE'])


if __name__ == '__main__':
    result = probe()
    repeat = probe()
    if result != repeat:
        raise ValueError('reproducibility failed')
    Path('pa_book_frozen_heterogeneity_probe_20260929.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({
        'identity': result['identity'],
        'gap_by_session': result['A_transition_gap']['by_session'],
        'concentration': {k: {a:b for a,b in v.items() if a not in ('counts','shares')}
                          for k,v in result['B_session_concentration'].items()},
        'pairs': {k:{a:b for a,b in v.items() if a in ('samples','runs','sessions','total_observed_duration_seconds')}
                  for k,v in result['C_pair_persistence'].items()},
        'overlap': {k:{a:b for a,b in v.items() if a != 'rows'} for k,v in result['D_conflict_overlap'].items()},
        'reproducible': True}, indent=2))
