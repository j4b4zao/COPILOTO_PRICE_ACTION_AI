from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

HORIZONS = (1, 3, 5, 10)


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _txt(value):
    return str(value if value is not None else '').strip().upper()


def _direction_from_num(value, eps=1e-12):
    value = _num(value)
    if value is None or abs(value) <= eps:
        return 'NEUTRAL'
    return 'BUY' if value > 0 else 'SELL'


def _context_direction(sample):
    structure = sample.get('structure') or {}
    pa = sample.get('price_action') or {}
    trend = _txt(structure.get('trend'))
    bias = _txt(pa.get('bias'))
    if trend in {'UP', 'BULLISH'} and bias == 'BUY':
        return 'BUY'
    if trend in {'DOWN', 'BEARISH'} and bias == 'SELL':
        return 'SELL'
    return 'MIXED'


def _micro_direction(sample):
    alignment = _txt(sample.get('alignment'))
    if alignment == 'BULLISH_ALIGNED':
        return 'BUY'
    if alignment == 'BEARISH_ALIGNED':
        return 'SELL'
    if alignment == 'DIVERGENT':
        tt = _direction_from_num(sample.get('recent_delta'))
        book = _direction_from_num(sample.get('imbalance'))
        if tt == 'BUY' and book == 'SELL':
            return 'DIVERGENT_TT_BUY_BOOK_SELL'
        if tt == 'SELL' and book == 'BUY':
            return 'DIVERGENT_TT_SELL_BOOK_BUY'
        return 'DIVERGENT_UNRESOLVED'
    return 'NEUTRAL'


def _bucket(sample):
    ctx = _context_direction(sample)
    micro = _micro_direction(sample)
    if ctx == 'BUY' and micro == 'BUY':
        return 'CONTEXT_BUY_MICRO_BUY'
    if ctx == 'SELL' and micro == 'SELL':
        return 'CONTEXT_SELL_MICRO_SELL'
    if ctx == 'BUY' and micro == 'SELL':
        return 'CONTEXT_BUY_MICRO_SELL'
    if ctx == 'SELL' and micro == 'BUY':
        return 'CONTEXT_SELL_MICRO_BUY'
    if ctx == 'BUY' and micro.startswith('DIVERGENT_'):
        return f'CONTEXT_BUY_{micro}'
    if ctx == 'SELL' and micro.startswith('DIVERGENT_'):
        return f'CONTEXT_SELL_{micro}'
    if ctx in {'BUY', 'SELL'} and micro == 'NEUTRAL':
        return f'CONTEXT_{ctx}_MICRO_NEUTRAL'
    return 'OTHER_READY_CONTEXT'


def _stats(values):
    n = len(values)
    if not n:
        return {'n': 0, 'mean_delta': None, 'median_delta': None, 'positive_rate': None, 'negative_rate': None, 'zero_rate': None}
    return {
        'n': n,
        'mean_delta': sum(values) / n,
        'median_delta': statistics.median(values),
        'positive_rate': sum(v > 0 for v in values) / n,
        'negative_rate': sum(v < 0 for v in values) / n,
        'zero_rate': sum(v == 0 for v in values) / n,
    }


def audit(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('phase') != 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE':
        raise ValueError('RC54_4_REQUIRES_RC54_3_2_WARMED_SESSION')
    if payload.get('status') not in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}:
        raise ValueError('RC54_4_REQUIRES_COMPLETED_SESSION')
    if not payload.get('price_capture'):
        raise ValueError('RC54_4_REQUIRES_SYNCHRONIZED_PRICE')
    if not payload.get('observational_only', False):
        raise ValueError('RC54_4_REQUIRES_OBSERVATIONAL_ONLY_SESSION')

    samples = payload.get('samples') or []
    ready_indices = [i for i, s in enumerate(samples) if bool(s.get('context_ready'))]
    buckets = {}
    counts = Counter()

    for i in ready_indices:
        b = _bucket(samples[i])
        counts[b] += 1
        buckets.setdefault(b, []).append(i)

    results = {}
    for name, indices in buckets.items():
        horizons = {}
        for h in HORIZONS:
            deltas = []
            for i in indices:
                j = i + h
                if j >= len(samples):
                    continue
                if not bool(samples[j].get('context_ready')):
                    continue
                p0 = _num(samples[i].get('last_price'))
                p1 = _num(samples[j].get('last_price'))
                if p0 is not None and p1 is not None:
                    deltas.append(p1 - p0)
            horizons[str(h)] = _stats(deltas)
        results[name] = {'occurrences': len(indices), 'horizons': horizons}

    return {
        'status': 'RC54_4_CONTEXT_QUALIFIED_ORDER_FLOW_AUDIT_COMPLETED',
        'samples': len(samples),
        'ready_samples': len(ready_indices),
        'excluded_not_ready_samples': len(samples) - len(ready_indices),
        'bucket_counts': dict(counts),
        'buckets': results,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.4: auditoria T&T + Book condicionada a Market Structure + PA bias READY.')
    p.add_argument('session_path')
    a = p.parse_args(argv)
    r = audit(a.session_path)
    print('PROFIT_RTD_RC54_4_CONTEXT_QUALIFIED_ORDER_FLOW_AUDITOR=COMPLETED')
    print(f"status={r['status']}")
    print(f"samples={r['samples']}")
    print(f"ready_samples={r['ready_samples']}")
    print(f"excluded_not_ready_samples={r['excluded_not_ready_samples']}")
    print('bucket_counts=' + json.dumps(r['bucket_counts'], sort_keys=True, separators=(',', ':')))
    for name in sorted(r['buckets']):
        data = r['buckets'][name]
        print(f"bucket={name} occurrences={data['occurrences']} horizons=" + json.dumps(data['horizons'], sort_keys=True, separators=(',', ':')))
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
