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


def _trade_context_ready(sample):
    return bool(sample.get('trade_context_ready', sample.get('context_ready', False)))


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


def incremental_identifiability(samples):
    context_bucket_sets = {}
    for sample in samples:
        if not _trade_context_ready(sample):
            continue
        context = _context_direction(sample)
        if context in {'BUY', 'SELL'}:
            context_bucket_sets.setdefault(context, set()).add(_bucket(sample))
    by_context = {
        context: {
            'distinct_micro_buckets': sorted(bucket_names),
            'distinct_micro_bucket_count': len(bucket_names),
            'incremental_effect_identifiable': len(bucket_names) >= 2,
        }
        for context, bucket_names in sorted(context_bucket_sets.items())
    }
    return {
        'by_context': by_context,
        'identifiable_contexts': [
            context for context, data in by_context.items()
            if data['incremental_effect_identifiable']
        ],
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
    if payload.get('data_ready') is not True:
        raise ValueError('RC54_4_REQUIRES_DATA_READY_SESSION')

    samples = payload.get('samples') or []
    ready_indices = [i for i, s in enumerate(samples) if _trade_context_ready(s)]
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
                if not _trade_context_ready(samples[j]):
                    continue
                p0 = _num(samples[i].get('last_price'))
                p1 = _num(samples[j].get('last_price'))
                if p0 is not None and p1 is not None:
                    deltas.append(p1 - p0)
            horizons[str(h)] = _stats(deltas)
        results[name] = {'occurrences': len(indices), 'horizons': horizons}

    identifiability = incremental_identifiability(samples)

    return {
        'status': 'RC54_4_CONTEXT_QUALIFIED_ORDER_FLOW_AUDIT_COMPLETED',
        'samples': len(samples),
        'ready_samples': len(ready_indices),
        'excluded_not_ready_samples': len(samples) - len(ready_indices),
        'bucket_counts': dict(counts),
        'buckets': results,
        'incremental_identifiability_by_context': identifiability['by_context'],
        'incrementally_identifiable_contexts': identifiability['identifiable_contexts'],
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
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
    print('incremental_identifiability_by_context=' + json.dumps(r['incremental_identifiability_by_context'], sort_keys=True, separators=(',', ':')))
    for name in sorted(r['buckets']):
        data = r['buckets'][name]
        print(f"bucket={name} occurrences={data['occurrences']} horizons=" + json.dumps(data['horizons'], sort_keys=True, separators=(',', ':')))
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
