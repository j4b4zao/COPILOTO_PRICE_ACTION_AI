from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_CYCLES = 600
DEFAULT_INTERVAL = 0.25
MIN_INDEPENDENT_EXTENDED_SESSIONS = 3


def protocol(symbol: str, cycles: int = DEFAULT_CYCLES, interval: float = DEFAULT_INTERVAL):
    return {
        'status': 'EXTENDED_OOS_VALIDATION_PROTOCOL_READY',
        'symbol': symbol,
        'cycles_per_session': int(cycles),
        'interval_seconds': float(interval),
        'minimum_independent_sessions': MIN_INDEPENDENT_EXTENDED_SESSIONS,
        'frozen_pattern_thresholds': True,
        'frozen_predictive_stability_thresholds': True,
        'collection_command': (
            f'python -m tools.profit_rtd_book_reconciliation {symbol} '
            f'--cycles {int(cycles)} --interval {float(interval)} --execute'
        ),
        'post_collection_sequence': [
            'SESSION_INTEGRITY_GATE',
            'OOS_PATTERN_AUDITOR_RC53_6',
            'PREDICTIVE_STABILITY_GATE_RC53_7',
        ],
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('symbol')
    p.add_argument('--cycles', type=int, default=DEFAULT_CYCLES)
    p.add_argument('--interval', type=float, default=DEFAULT_INTERVAL)
    p.add_argument('--output')
    args = p.parse_args()
    result = protocol(args.symbol, args.cycles, args.interval)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
        print(f'output_path={out.resolve()}')
    print('PROFIT_RTD_BOOK_EXTENDED_OOS_VALIDATION_PROTOCOL=READY')
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            print(f'{key}=' + json.dumps(value, sort_keys=True, separators=(',', ':')))
        else:
            print(f'{key}={value}')


if __name__ == '__main__':
    main()
