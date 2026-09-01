from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys

from tools.profit_rtd_rc54_5_3_market_activity_preflight import check_market_activity
from tools.profit_rtd_rc54_3_2_warmed_session import run_warmed_session
from tools.profit_rtd_rc54_4_context_qualified_order_flow_auditor import incremental_identifiability


class _ConciseProgress:
    def __init__(self, target, every=50):
        self.target = target
        self.every = max(1, int(every))
        self.buffer = ''
        self.last_state = {}

    def write(self, text):
        self.buffer += str(text)
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            self._emit(line)
        return len(text)

    def flush(self):
        if self.buffer:
            self._emit(self.buffer)
            self.buffer = ''
        self.target.flush()

    def _emit(self, line):
        if 'error=' in line.lower() or line.startswith('PROFIT_RTD_RC54'):
            self.target.write(line + '\n')
            return
        if not line.startswith(('[RC54.3.2 WARMUP]', '[RC54.3.2]')):
            return
        match = re.search(r'cycle=(\d+)/(\d+)', line)
        cycle = int(match.group(1)) if match else 0
        phase = 'WARMUP' if line.startswith('[RC54.3.2 WARMUP]') else 'SESSION'
        state = tuple(
            re.search(pattern, line).group(1) if re.search(pattern, line) else None
            for pattern in (
                r'structure=([^ ]+)', r'pa_bias=([^ ]+)',
                r'history_ready=([^ ]+)', r'trade_context_ready=([^ ]+)', r'ready=([^ ]+)',
            )
        )
        changed = state != self.last_state.get(phase)
        if changed or cycle == 1 or cycle % self.every == 0:
            self.target.write(line + '\n')
        self.last_state[phase] = state


def _call_with_output(function, *, concise_output, progress_every, **kwargs):
    if not concise_output:
        return function(**kwargs)
    stream = _ConciseProgress(sys.stdout, every=progress_every)
    with contextlib.redirect_stdout(stream):
        result = function(**kwargs)
    stream.flush()
    return result


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
    require_trade_context_at_start=False,
    concise_output=False,
    progress_every=50,
    output_dir=None,
):
    preflight = _call_with_output(
        check_market_activity,
        concise_output=concise_output,
        progress_every=progress_every,
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
            'warmup_started': False,
            'session_started': False,
            'session': None,
            'incremental_identifiability_by_context': {},
            'incrementally_identifiable_contexts': [],
            'observational_only': True,
            'predictive_claim_allowed': False,
            'score_influence_allowed': False,
            'risk_influence_allowed': False,
            'decision_influence_allowed': False,
            'order_execution_allowed': False,
        }

    session = _call_with_output(
        lambda **kwargs: run_warmed_session(symbol, **kwargs),
        concise_output=concise_output,
        progress_every=progress_every,
        cycles=cycles,
        interval=interval,
        max_warmup_cycles=max_warmup_cycles,
        require_trade_context_at_start=require_trade_context_at_start,
        output_dir=output_dir,
    )
    capture_started = session.get('status') in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}
    identifiability = incremental_identifiability(session.get('samples') or []) if capture_started else {
        'by_context': {}, 'identifiable_contexts': [],
    }
    return {
        'status': 'SESSION_COMPLETED' if capture_started else 'SESSION_ABORTED_AFTER_PREFLIGHT',
        'symbol': str(symbol or '').strip().upper(),
        'preflight': preflight,
        'warmup_started': True,
        'session_started': capture_started,
        'session': session,
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
    p.add_argument('--require-trade-context-at-start', action='store_true')
    p.add_argument('--concise-output', action='store_true')
    p.add_argument('--progress-every', type=int, default=50)
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
        require_trade_context_at_start=a.require_trade_context_at_start,
        concise_output=a.concise_output,
        progress_every=a.progress_every,
        output_dir=a.output_dir,
    )

    print(f"PROFIT_RTD_RC54_5_4={r['status']}")
    print('symbol=' + r['symbol'])
    print('preflight_status=' + r['preflight']['status'])
    print('preflight_reasons=' + ('|'.join(r['preflight']['reasons']) if r['preflight']['reasons'] else 'OK'))
    print('warmup_started=' + str(r['warmup_started']))
    print('session_started=' + str(r['session_started']))
    if r['session'] is not None:
        s = r['session']
        print('session_status=' + str(s.get('status')))
        print('session_data_ready=' + str(s.get('data_ready')))
        print('session_trade_context_ready=' + str(s.get('trade_context_ready')))
        print('session_output_path=' + str(s.get('output_path', '')))
        print('session_reasons=' + ('|'.join(s.get('reasons') or []) if s.get('reasons') else 'OK'))
        print('incrementally_identifiable_contexts=' + json.dumps(r['incrementally_identifiable_contexts'], separators=(',', ':')))
        print('incremental_identifiability_by_context=' + json.dumps(r['incremental_identifiability_by_context'], sort_keys=True, separators=(',', ':')))
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('risk_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    return 0 if r['status'] == 'SESSION_COMPLETED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
