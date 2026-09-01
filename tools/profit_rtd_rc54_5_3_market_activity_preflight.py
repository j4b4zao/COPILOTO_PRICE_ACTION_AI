from __future__ import annotations

import argparse
import time

from tools.profit_rtd_order_flow_combined_session import _build_sources


def _last_price(context):
    candle = getattr(getattr(context, 'market', None), 'last_candle', None)
    value = getattr(candle, 'close', None) if candle is not None else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candle_count(context):
    try:
        return int(getattr(getattr(context, 'market', None), 'candle_count', 0) or 0)
    except (TypeError, ValueError):
        return 0


def check_market_activity(*, cycles=120, interval=0.25, min_analyzable=10, min_price_changes=2, min_candle_growth=1, sleeper=time.sleep, collector=None):
    if int(cycles) < 1 or float(interval) < 0:
        raise ValueError('cycles/interval inválidos.')
    if min_analyzable < 1 or min_price_changes < 0 or min_candle_growth < 0:
        raise ValueError('thresholds inválidos.')

    if collector is None:
        collector, _ = _build_sources()

    analyzable = 0
    skipped = 0
    errors = 0
    prices = []
    candle_counts = []

    for cycle in range(1, int(cycles) + 1):
        try:
            context = collector.get_data()
            if context is None:
                skipped += 1
            else:
                analyzable += 1
                price = _last_price(context)
                if price is not None:
                    prices.append(price)
                candle_counts.append(_candle_count(context))
        except Exception:
            errors += 1

        if cycle < int(cycles) and float(interval) > 0:
            sleeper(float(interval))

    price_changes = sum(a != b for a, b in zip(prices, prices[1:]))
    candle_growth = (max(candle_counts) - min(candle_counts)) if candle_counts else 0
    active = analyzable >= int(min_analyzable) and price_changes >= int(min_price_changes) and candle_growth >= int(min_candle_growth)

    reasons = []
    if analyzable < int(min_analyzable):
        reasons.append('INSUFFICIENT_ANALYZABLE_UPDATES')
    if price_changes < int(min_price_changes):
        reasons.append('INSUFFICIENT_PRICE_MOVEMENT')
    if candle_growth < int(min_candle_growth):
        reasons.append('NO_NEW_M1_CANDLE_PROGRESS')

    return {
        'status': 'MARKET_ACTIVITY_READY' if active else 'MARKET_ACTIVITY_NOT_READY',
        'active': active,
        'cycles': int(cycles),
        'analyzable': analyzable,
        'skipped': skipped,
        'errors': errors,
        'price_changes': price_changes,
        'candle_growth': candle_growth,
        'reasons': reasons,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.5.3: preflight de atividade real antes do warm-up RC54.')
    p.add_argument('--cycles', type=int, default=120)
    p.add_argument('--interval', type=float, default=0.25)
    p.add_argument('--min-analyzable', type=int, default=10)
    p.add_argument('--min-price-changes', type=int, default=2)
    p.add_argument('--min-candle-growth', type=int, default=1)
    a = p.parse_args(argv)
    r = check_market_activity(cycles=a.cycles, interval=a.interval, min_analyzable=a.min_analyzable, min_price_changes=a.min_price_changes, min_candle_growth=a.min_candle_growth)
    print(f"PROFIT_RTD_RC54_5_3={r['status']}")
    for key in ('active','cycles','analyzable','skipped','errors','price_changes','candle_growth'):
        print(f'{key}={r[key]}')
    print('reasons=' + ('|'.join(r['reasons']) if r['reasons'] else 'OK'))
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('risk_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    return 0 if r['active'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
