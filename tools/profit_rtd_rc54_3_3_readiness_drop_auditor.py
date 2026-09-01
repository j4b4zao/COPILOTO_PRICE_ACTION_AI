from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

BAD_TRENDS = {'', 'UNKNOWN'}
BAD_BIASES = {'', 'NONE', 'UNKNOWN'}


def _text(value):
    return str(value if value is not None else '').strip().upper()


def _trade_context_ready(sample):
    return bool(sample.get('trade_context_ready', sample.get('context_ready', False)))


def _classify_drop(sample):
    structure = sample.get('structure') or {}
    pa = sample.get('price_action') or {}
    trend = _text(structure.get('trend'))
    bias = _text(pa.get('bias'))
    reasons = []
    if trend in BAD_TRENDS:
        reasons.append('STRUCTURE_TREND_NOT_READY')
    if bias in BAD_BIASES:
        reasons.append('PA_BIAS_NOT_READY')
    if not reasons:
        if 'valid' in structure:
            if not bool(structure.get('valid')):
                reasons.append('STRUCTURE_VALID_FALSE')
            else:
                reasons.append('READY_FLAG_INCONSISTENT_WITH_COMPONENTS')
        else:
            reasons.append('STRUCTURE_VALID_FALSE_OR_UNRECORDED')
    return reasons


def audit(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('phase') != 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE':
        raise ValueError('RC54_3_3_REQUIRES_RC54_3_2_SESSION')
    if payload.get('status') not in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}:
        raise ValueError('RC54_3_3_REQUIRES_COMPLETED_SESSION')
    if not payload.get('price_capture'):
        raise ValueError('RC54_3_3_REQUIRES_SYNCHRONIZED_PRICE')
    if not payload.get('observational_only', False):
        raise ValueError('RC54_3_3_REQUIRES_OBSERVATIONAL_ONLY_SESSION')

    samples = payload.get('samples') or []
    drops = []
    cause_counts = Counter()
    combination_counts = Counter()
    ready_runs = []
    drop_runs = []

    current_ready = None
    run_start = None
    run_sample_count = 0
    previous_cycle = None

    for idx, sample in enumerate(samples):
        ready = _trade_context_ready(sample)
        cycle = int(sample.get('cycle', idx + 1))
        if current_ready is None:
            current_ready = ready
            run_start = cycle
            run_sample_count = 1
        elif ready != current_ready:
            target = ready_runs if current_ready else drop_runs
            target.append({'start_cycle': run_start, 'end_cycle': previous_cycle, 'sample_count': run_sample_count})
            current_ready = ready
            run_start = cycle
            run_sample_count = 1
        else:
            run_sample_count += 1

        if not ready:
            reasons = _classify_drop(sample)
            for reason in reasons:
                cause_counts[reason] += 1
            combination_counts['+'.join(sorted(reasons))] += 1
            drops.append({
                'cycle': cycle,
                'timestamp': sample.get('timestamp'),
                'structure_trend': _text((sample.get('structure') or {}).get('trend')),
                'structure_valid': (sample.get('structure') or {}).get('valid', 'UNRECORDED'),
                'pa_bias': _text((sample.get('price_action') or {}).get('bias')),
                'alignment': sample.get('alignment'),
                'last_price': sample.get('last_price'),
                'reasons': reasons,
            })
        previous_cycle = cycle

    if current_ready is not None:
        target = ready_runs if current_ready else drop_runs
        target.append({'start_cycle': run_start, 'end_cycle': previous_cycle, 'sample_count': run_sample_count})

    n = len(samples)
    drop_count = len(drops)
    ready_count = n - drop_count
    longest_drop_run = max((r['sample_count'] for r in drop_runs), default=0)
    longest_ready_run = max((r['sample_count'] for r in ready_runs), default=0)

    if drop_count == 0:
        verdict = 'READINESS_STABLE'
    elif cause_counts.get('STRUCTURE_TREND_NOT_READY', 0) or cause_counts.get('PA_BIAS_NOT_READY', 0):
        verdict = 'READINESS_DROPS_EXPLAINED_BY_CONTEXT_TRANSITIONS'
    elif cause_counts.get('STRUCTURE_VALID_FALSE', 0):
        verdict = 'READINESS_DROPS_EXPLAINED_BY_STRUCTURE_VALIDITY'
    else:
        verdict = 'READINESS_DROPS_REQUIRE_STRUCTURE_VALID_CAPTURE'

    return {
        'status': 'RC54_3_3_READINESS_DROP_AUDIT_COMPLETED',
        'source_session': str(path),
        'samples': n,
        'ready_samples': ready_count,
        'drop_samples': drop_count,
        'ready_rate': ready_count / n if n else 0.0,
        'drop_rate': drop_count / n if n else 0.0,
        'cause_counts': dict(cause_counts),
        'combination_counts': dict(combination_counts),
        'drop_runs': drop_runs,
        'ready_runs': ready_runs,
        'longest_drop_run': longest_drop_run,
        'longest_ready_run': longest_ready_run,
        'first_drop_cycle': drops[0]['cycle'] if drops else None,
        'last_drop_cycle': drops[-1]['cycle'] if drops else None,
        'verdict': verdict,
        'drops': drops,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.3.3: auditoria das quedas de readiness durante sessão warmed.')
    p.add_argument('session_path')
    a = p.parse_args(argv)
    r = audit(a.session_path)
    print('PROFIT_RTD_RC54_3_3_READINESS_DROP_AUDITOR=COMPLETED')
    print(f"status={r['status']}")
    for key in ('samples','ready_samples','drop_samples','ready_rate','drop_rate','longest_drop_run','longest_ready_run','first_drop_cycle','last_drop_cycle'):
        print(f'{key}={r[key]}')
    print('cause_counts=' + json.dumps(r['cause_counts'], sort_keys=True, separators=(',', ':')))
    print('combination_counts=' + json.dumps(r['combination_counts'], sort_keys=True, separators=(',', ':')))
    print('drop_runs=' + json.dumps(r['drop_runs'], separators=(',', ':')))
    print(f"verdict={r['verdict']}")
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
