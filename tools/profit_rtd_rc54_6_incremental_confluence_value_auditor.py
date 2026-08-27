from __future__ import annotations

import argparse
import json
from pathlib import Path

HORIZONS = ('1', '3', '5', '10')


def _context_side(bucket):
    if bucket.startswith('CONTEXT_BUY_'):
        return 'BUY'
    if bucket.startswith('CONTEXT_SELL_'):
        return 'SELL'
    return 'OTHER'


def _weighted_mean(parts):
    total_n = sum(int(p.get('n') or 0) for p in parts)
    if total_n <= 0:
        return {'n': 0, 'mean_delta': None}
    weighted = 0.0
    used = 0
    for p in parts:
        n = int(p.get('n') or 0)
        mean = p.get('mean_delta')
        if n > 0 and isinstance(mean, (int, float)):
            weighted += float(mean) * n
            used += n
    if used <= 0:
        return {'n': 0, 'mean_delta': None}
    return {'n': used, 'mean_delta': weighted / used}


def audit(accumulator_payload):
    if accumulator_payload.get('status') != 'RC54_5_MULTI_SESSION_EVIDENCE_ACCUMULATION_COMPLETED':
        raise ValueError('RC54_6_REQUIRES_RC54_5_ACCUMULATOR_OUTPUT')

    buckets = accumulator_payload.get('buckets') or {}
    context_baselines = {}

    for side in ('BUY', 'SELL'):
        side_buckets = [data for name, data in buckets.items() if _context_side(name) == side]
        context_baselines[side] = {
            h: _weighted_mean([(b.get('horizons') or {}).get(h, {}) for b in side_buckets])
            for h in HORIZONS
        }

    comparisons = {}
    for name, data in sorted(buckets.items()):
        side = _context_side(name)
        if side not in {'BUY', 'SELL'}:
            continue
        horizons = {}
        for h in HORIZONS:
            bucket_stats = (data.get('horizons') or {}).get(h, {})
            baseline = context_baselines[side][h]
            bucket_mean = bucket_stats.get('mean_delta')
            baseline_mean = baseline.get('mean_delta')
            incremental = None
            if isinstance(bucket_mean, (int, float)) and isinstance(baseline_mean, (int, float)):
                incremental = float(bucket_mean) - float(baseline_mean)
            horizons[h] = {
                'bucket_n': int(bucket_stats.get('n') or 0),
                'bucket_mean_delta': bucket_mean,
                'context_baseline_n': baseline.get('n', 0),
                'context_baseline_mean_delta': baseline_mean,
                'incremental_mean_delta': incremental,
            }
        comparisons[name] = {
            'context_side': side,
            'occurrences': int(data.get('occurrences') or 0),
            'sessions': int(data.get('sessions') or 0),
            'evidence_threshold_met': bool(data.get('evidence_threshold_met', False)),
            'horizons': horizons,
        }

    return {
        'status': 'RC54_6_INCREMENTAL_CONFLUENCE_VALUE_AUDIT_COMPLETED',
        'source_session_count': int(accumulator_payload.get('session_count') or 0),
        'context_baselines': context_baselines,
        'comparisons': comparisons,
        'interpretation_rule': 'Incremental delta compares each microstructure bucket with the pooled BUY/SELL context baseline; it does not establish causality or predictive validity.',
        'verdict': 'INCREMENTAL_VALUE_REQUIRES_MULTI_SESSION_ROBUSTNESS_VALIDATION',
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.6: compara microestrutura com baseline de contexto PA/estrutura.')
    p.add_argument('accumulator_json')
    a = p.parse_args(argv)
    payload = json.loads(Path(a.accumulator_json).read_text(encoding='utf-8'))
    r = audit(payload)
    print('PROFIT_RTD_RC54_6_INCREMENTAL_CONFLUENCE_VALUE_AUDITOR=COMPLETED')
    print(f"source_session_count={r['source_session_count']}")
    for side, data in r['context_baselines'].items():
        print('baseline=' + side + ' ' + json.dumps(data, sort_keys=True, separators=(',', ':')))
    for name, data in r['comparisons'].items():
        print('comparison=' + name + ' ' + json.dumps(data, sort_keys=True, separators=(',', ':')))
    print(f"verdict={r['verdict']}")
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
