from __future__ import annotations

import argparse
import json

from tools.profit_rtd_rc54_5_3_market_activity_preflight import check_market_activity
from tools.profit_rtd_rc54_3_2_warmed_session import run_warmed_session


def run_orchestrated_session(
    symbol,
    *,
    preflight_cycles=120,
    preflight_interval=0.25,
    min_analyzable=10,
    min_price_changes=2,
    min_candle_growth=1,
    cycles=600,
    interval=0.25,
    max_warmup_cycles=2400,
    output_dir=None,
):
    preflight = check_market_activity(
        cycles=preflight_cycles,
        interval=preflight_interval,
        min_analyzable=min_analyzable,
        min_price_changes=min_price_changes,
        min_candle_growth=min_candle_growth,
    )

    if not preflight['active']:
        return {
            'status': 'ABORTED_MARKET_ACTIVITY_NOT_READY',
            'symbol': str(symbol or '').strip().upper(),
            'preflight': preflight,
            'session_started': False,
            'session': None,
            'observational_only': True,
            'predictive_claim_allowed': False,
            'score_influence_allowed': False,
            'decision_influence_allowed': False,
            'order_execution_allowed': False,
        }

    session = run_warmed_session(
        symbol,
        cycles=cycles,
        interval=interval,
        max_warmup_cycles=max_warmup_cycles,
        output_dir=output_dir,
    )
    return {
        'status': 'SESSION_COMPLETED' if session.get('status') in {'COMPLETED','COMPLETED_WITH_WARNINGS'} else 'SESSION_ABORTED_AFTER_PREFLIGHT',
        'symbol': str(symbol or '').strip().upper(),
        'preflight': preflight,
        'session_started': True,
        'session': session,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.5.4: preflight + warm-up + sessão RC54.3.2 em um único runner.')
    p.add_argument('symbol')
    p.add_argument('--preflight-cycles', type=int, default=120)
    p.add_argument('--preflight-interval', type=float, default=0.25)
    p.add_argument('--min-analyzable', type=int, default=10)
    p.add_argument('--min-price-changes', type=int, default=2)
    p.add_argument('--min-candle-growth', type=int, default=1)
    p.add_argument('--cycles', type=int, default=600)
    p.add_argument('--interval', type=float, default=0.25)
    p.add_argument('--max-warmup-cycles', type=int, default=2400)
    p.add_argument('--output-dir')
    a = p.parse_args(argv)

    r = run_orchestrated_session(
        a.symbol,
        preflight_cycles=a.preflight_cycles,
        preflight_interval=a.preflight_interval,
        min_analyzable=a.min_analyzable,
        min_price_changes=a.min_price_changes,
        min_candle_growth=a.min_candle_growth,
        cycles=a.cycles,
        interval=a.interval,
        max_warmup_cycles=a.max_warmup_cycles,
        output_dir=a.output_dir,
    )

    print(f"PROFIT_RTD_RC54_5_4={r['status']}")
    print('symbol=' + r['symbol'])
    print('preflight_status=' + r['preflight']['status'])
    print('preflight_reasons=' + ('|'.join(r['preflight']['reasons']) if r['preflight']['reasons'] else 'OK'))
    print('session_started=' + str(r['session_started']))
    if r['session'] is not None:
        s = r['session']
        print('session_status=' + str(s.get('status')))
        print('session_output_path=' + str(s.get('output_path', '')))
        print('session_reasons=' + ('|'.join(s.get('reasons') or []) if s.get('reasons') else 'OK'))
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    return 0 if r['status'] == 'SESSION_COMPLETED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
