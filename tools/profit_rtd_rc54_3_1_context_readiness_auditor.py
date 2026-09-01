from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

UNKNOWN = {'', 'UNKNOWN', 'NONE', 'NEUTRAL', 'N/A', 'NULL'}


def _text(value):
    return str(value if value is not None else '').strip().upper()


def _meaningful(value):
    return _text(value) not in UNKNOWN


def audit(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('phase') != 'RC54.3_SYNCHRONIZED_PA_STRUCTURE_CONTEXT_CAPTURE':
        raise ValueError('RC54_3_1_REQUIRES_RC54_3_SESSION')
    if payload.get('status') not in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}:
        raise ValueError('RC54_3_1_REQUIRES_COMPLETED_SESSION')
    if not payload.get('price_capture'):
        raise ValueError('RC54_3_1_REQUIRES_SYNCHRONIZED_PRICE')
    if not payload.get('observational_only', False):
        raise ValueError('RC54_3_1_REQUIRES_OBSERVATIONAL_ONLY_SESSION')

    samples = payload.get('samples') or []
    structure_trends = Counter()
    pa_biases = Counter()
    pa_trends = Counter()
    bar_classes = Counter()
    brooks_signal_phases = Counter()
    brooks_composites = Counter()

    structure_ready = 0
    pa_bias_ready = 0
    structural_event_ready = 0
    brooks_ready = 0
    combined_ready = 0

    for sample in samples:
        structure = sample.get('structure') or {}
        pa = sample.get('price_action') or {}

        st = _text(structure.get('trend')) or 'EMPTY'
        pb = _text(pa.get('bias')) or 'EMPTY'
        pt = _text(pa.get('trend')) or 'EMPTY'
        bc = _text(pa.get('bar_classification')) or 'EMPTY'
        bsp = _text(pa.get('brooks_signal_phase')) or 'EMPTY'
        bcp = _text(pa.get('brooks_composite_pattern')) or 'EMPTY'
        structure_trends[st] += 1
        pa_biases[pb] += 1
        pa_trends[pt] += 1
        bar_classes[bc] += 1
        brooks_signal_phases[bsp] += 1
        brooks_composites[bcp] += 1

        s_ready = _meaningful(st)
        p_ready = _meaningful(pb)
        event_ready = any(bool(structure.get(k)) for k in ('hh','hl','lh','ll','bos_up','bos_down','choch'))
        b_ready = any([
            _meaningful(bc),
            _meaningful(bsp),
            _meaningful(pa.get('brooks_signal_direction')),
            _meaningful(pa.get('brooks_signal_quality')),
            _meaningful(bcp),
            _meaningful(pa.get('brooks_composite_direction')),
            bool(pa.get('brooks_entry_triggered')),
            bool(pa.get('brooks_follow_through')),
            bool(pa.get('brooks_reversal_candidate')),
        ])

        structure_ready += int(s_ready)
        pa_bias_ready += int(p_ready)
        structural_event_ready += int(event_ready)
        brooks_ready += int(b_ready)
        combined_ready += int(s_ready and (p_ready or b_ready))

    n = len(samples)
    def rate(count):
        return count / n if n else 0.0

    readiness = {
        'structure_ready': structure_ready,
        'structure_ready_rate': rate(structure_ready),
        'pa_bias_ready': pa_bias_ready,
        'pa_bias_ready_rate': rate(pa_bias_ready),
        'structural_event_ready': structural_event_ready,
        'structural_event_ready_rate': rate(structural_event_ready),
        'brooks_ready': brooks_ready,
        'brooks_ready_rate': rate(brooks_ready),
        'combined_context_ready': combined_ready,
        'combined_context_ready_rate': rate(combined_ready),
    }

    if n == 0:
        verdict = 'NO_ANALYZABLE_SAMPLES'
    elif combined_ready == 0:
        verdict = 'CONTEXT_NOT_READY_RECAPTURE_WITH_WARM_HISTORY'
    elif rate(combined_ready) < 0.50:
        verdict = 'CONTEXT_PARTIALLY_READY_MORE_WARM_HISTORY_REQUIRED'
    else:
        verdict = 'CONTEXT_READY_FOR_OBSERVATIONAL_CONFLUENCE_AUDIT'

    return {
        'status': 'RC54_3_1_CONTEXT_READINESS_AUDIT_COMPLETED',
        'source_session': str(path),
        'samples': n,
        'readiness': readiness,
        'distributions': {
            'structure_trend': dict(structure_trends),
            'pa_bias': dict(pa_biases),
            'pa_trend': dict(pa_trends),
            'bar_classification': dict(bar_classes),
            'brooks_signal_phase': dict(brooks_signal_phases),
            'brooks_composite_pattern': dict(brooks_composites),
        },
        'verdict': verdict,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.3.1: auditoria de maturidade do contexto PA/Structure sincronizado.')
    p.add_argument('session_path')
    a = p.parse_args(argv)
    r = audit(a.session_path)
    print('PROFIT_RTD_RC54_3_1_CONTEXT_READINESS_AUDITOR=COMPLETED')
    print(f"status={r['status']}")
    print(f"samples={r['samples']}")
    for key, value in r['readiness'].items():
        print(f'{key}={value}')
    for key, value in r['distributions'].items():
        print(f'{key}=' + json.dumps(value, sort_keys=True, separators=(',', ':')))
    print(f"verdict={r['verdict']}")
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
