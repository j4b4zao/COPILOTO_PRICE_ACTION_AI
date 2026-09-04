from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.profit_rtd_book_oos_pattern_auditor import audit

MIN_PATTERN_N = 10
MIN_SESSIONS = 3
MAX_SESSION_SHARE = 0.60
MIN_DIRECTIONAL_RATE = 0.55
MIN_EFFECT_ABS = 5.0
MIN_STABLE_HORIZONS = 2


def _direction(pattern: str) -> str:
    if pattern.startswith('NEGATIVE_') or ' > NEGATIVE_' in pattern:
        return 'NEGATIVE'
    if pattern.startswith('POSITIVE_') or ' > POSITIVE_' in pattern:
        return 'POSITIVE'
    return 'UNKNOWN'


def _assess_pattern(item: dict) -> dict:
    reasons = []
    pattern = item.get('pattern', '')
    n = int(item.get('n', 0) or 0)
    sessions_count = int(item.get('sessions_count', 0) or 0)
    max_session_share = float(item.get('max_session_share', 0.0) or 0.0)
    direction = _direction(pattern)

    if n < MIN_PATTERN_N:
        reasons.append('INSUFFICIENT_PATTERN_SAMPLE_SIZE')
    if sessions_count < MIN_SESSIONS:
        reasons.append('INSUFFICIENT_CROSS_SESSION_RECURRENCE')
    if max_session_share > MAX_SESSION_SHARE:
        reasons.append('EXCESSIVE_SINGLE_SESSION_CONCENTRATION')

    stable_horizons = []
    contradictory_horizons = []
    horizon_assessment = {}

    for h in ('1', '3', '5', '10'):
        stats = (item.get('horizons') or {}).get(h, {})
        hn = int(stats.get('n', 0) or 0)
        mean_delta = stats.get('mean_delta')
        pos_rate = float(stats.get('positive_rate', 0.0) or 0.0)
        neg_rate = float(stats.get('negative_rate', 0.0) or 0.0)
        zero_rate = float(stats.get('zero_rate', 0.0) or 0.0)

        if direction == 'NEGATIVE':
            directional_rate = neg_rate
            opposite_rate = pos_rate
            sign_ok = mean_delta is not None and mean_delta < 0
        elif direction == 'POSITIVE':
            directional_rate = pos_rate
            opposite_rate = neg_rate
            sign_ok = mean_delta is not None and mean_delta > 0
        else:
            directional_rate = max(pos_rate, neg_rate)
            opposite_rate = min(pos_rate, neg_rate)
            sign_ok = mean_delta not in (None, 0)

        effect_ok = mean_delta is not None and abs(float(mean_delta)) >= MIN_EFFECT_ABS
        rate_ok = directional_rate >= MIN_DIRECTIONAL_RATE
        horizon_ok = hn >= MIN_PATTERN_N and sign_ok and effect_ok and rate_ok

        if horizon_ok:
            stable_horizons.append(h)
        if mean_delta is not None and ((direction == 'NEGATIVE' and mean_delta > 0) or (direction == 'POSITIVE' and mean_delta < 0)):
            contradictory_horizons.append(h)

        horizon_assessment[h] = {
            'n': hn,
            'mean_delta': mean_delta,
            'directional_rate': directional_rate,
            'opposite_rate': opposite_rate,
            'zero_rate': zero_rate,
            'effect_ok': effect_ok,
            'directional_rate_ok': rate_ok,
            'sign_ok': sign_ok,
            'stable': horizon_ok,
        }

    if len(stable_horizons) < MIN_STABLE_HORIZONS:
        reasons.append('INSUFFICIENT_STABLE_HORIZONS')
    if contradictory_horizons:
        reasons.append('HORIZON_DIRECTION_CONTRADICTION')

    status = 'PREDICTIVE_STABILITY_MINIMUM_MET' if not reasons else 'PREDICTIVE_STABILITY_NOT_MET'
    return {
        'pattern': pattern,
        'direction': direction,
        'n': n,
        'sessions_count': sessions_count,
        'max_session_share': max_session_share,
        'stable_horizons': stable_horizons,
        'contradictory_horizons': contradictory_horizons,
        'horizons': horizon_assessment,
        'stability_status': status,
        'stability_reasons': reasons or ['MINIMUM_PREDICTIVE_STABILITY_GATES_MET'],
    }


def evaluate(paths):
    audited = audit(paths)
    candidates = [p for p in audited.get('top_patterns', []) if p.get('evidence_status') == 'AUDIT_EVIDENCE_MINIMUM_MET']
    assessed = [_assess_pattern(p) for p in candidates]
    passed = [p for p in assessed if p['stability_status'] == 'PREDICTIVE_STABILITY_MINIMUM_MET']
    return {
        'status': 'PREDICTIVE_STABILITY_GATE_COMPLETED',
        'patterns_with_minimum_audit_evidence': len(candidates),
        'patterns_passing_stability_gate': len(passed),
        'patterns': assessed,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('paths', nargs='+')
    p.add_argument('--output')
    args = p.parse_args()
    result = evaluate(args.paths)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
        print(f'output_path={out.resolve()}')
    print('PROFIT_RTD_BOOK_PREDICTIVE_STABILITY_GATE=COMPLETED')
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            print(f'{key}=' + json.dumps(value, sort_keys=True, separators=(',', ':')))
        else:
            print(f'{key}={value}')


if __name__ == '__main__':
    main()
