from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HORIZONS = (1, 3, 5, 10)


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _direction(value, eps=1e-12):
    value = _num(value)
    if value is None or abs(value) <= eps:
        return 'NEUTRAL'
    return 'BUY' if value > 0 else 'SELL'


def _divergence_type(sample):
    if str(sample.get('alignment') or '').upper() != 'DIVERGENT':
        return None
    tt = _direction(sample.get('recent_delta'))
    book = _direction(sample.get('imbalance'))
    if tt == 'BUY' and book == 'SELL':
        return 'TT_BUY_BOOK_SELL'
    if tt == 'SELL' and book == 'BUY':
        return 'TT_SELL_BOOK_BUY'
    return 'DIVERGENT_UNRESOLVED'


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
    if payload.get('status') != 'COMPLETED' or not payload.get('price_capture'):
        raise ValueError('RC54_2_REQUIRES_CLEAN_PRICE_SYNCHRONIZED_SESSION')
    if not payload.get('observational_only', False):
        raise ValueError('RC54_2_REQUIRES_OBSERVATIONAL_ONLY_SESSION')

    samples = payload.get('samples') or []
    groups = {k: [] for k in ('TT_BUY_BOOK_SELL', 'TT_SELL_BOOK_BUY', 'DIVERGENT_UNRESOLVED')}
    for i, sample in enumerate(samples):
        kind = _divergence_type(sample)
        if kind:
            groups[kind].append(i)

    result_groups = {}
    for kind, indices in groups.items():
        horizons = {}
        for h in HORIZONS:
            deltas = []
            for i in indices:
                j = i + h
                if j >= len(samples):
                    continue
                p0 = _num(samples[i].get('last_price'))
                p1 = _num(samples[j].get('last_price'))
                if p0 is not None and p1 is not None:
                    deltas.append(p1 - p0)
            horizons[str(h)] = _stats(deltas)
        result_groups[kind] = {'occurrences': len(indices), 'horizons': horizons}

    return {
        'status': 'RC54_2_DIRECTIONAL_DIVERGENCE_AUDIT_COMPLETED',
        'samples': len(samples),
        'divergent_occurrences': sum(len(v) for v in groups.values()),
        'groups': result_groups,
        'price_action_market_structure_integration': 'PENDING_SYNCHRONIZED_CONTEXT_CAPTURE',
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.2: decomposição direcional das divergências T&T + Book.')
    p.add_argument('session_path')
    a = p.parse_args(argv)
    r = audit(a.session_path)
    print('PROFIT_RTD_RC54_2_DIRECTIONAL_DIVERGENCE_AUDITOR=COMPLETED')
    print(f"status={r['status']}")
    print(f"samples={r['samples']}")
    print(f"divergent_occurrences={r['divergent_occurrences']}")
    for kind, data in r['groups'].items():
        print(f"divergence={kind} occurrences={data['occurrences']} horizons=" + json.dumps(data['horizons'], sort_keys=True, separators=(',', ':')))
    for key in ('price_action_market_structure_integration','observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
