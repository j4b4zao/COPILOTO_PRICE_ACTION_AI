from __future__ import annotations

import argparse
import time

from analysis.analysis_pipeline import AnalysisPipeline
from tools.profit_rtd_order_flow_combined_session import _build_sources


def _enum_value(value):
    return str(getattr(value, 'value', value)).strip().upper()


def context_ready(context):
    structure = context.structure
    pa = context.price_action
    structure_trend = _enum_value(structure.trend)
    pa_bias = str(pa.bias or 'NONE').strip().upper()
    structure_ok = bool(getattr(structure, 'valid', False)) and structure_trend not in {'', 'UNKNOWN'}
    pa_ok = pa_bias not in {'', 'NONE', 'UNKNOWN'}
    return structure_ok and pa_ok


def history_ready(context):
    structure = context.structure
    structure_trend = _enum_value(structure.trend)
    return bool(getattr(structure, 'valid', False)) and structure_trend not in {'', 'UNKNOWN'}


def warm_history(symbol, *, interval=0.25, max_warmup_cycles=4800, require_trade_context=False, sleeper=time.sleep, collector=None, pipeline=None):
    symbol = str(symbol or '').strip().upper()
    if not symbol:
        raise ValueError('symbol é obrigatório.')
    if int(max_warmup_cycles) < 1:
        raise ValueError('max_warmup_cycles deve ser >= 1.')
    if float(interval) < 0:
        raise ValueError('interval deve ser >= 0.')

    if collector is None or pipeline is None:
        collector, book_provider = _build_sources()
        pipeline = AnalysisPipeline(book_depth_service=book_provider)

    analyzable = 0
    skipped = 0
    errors = 0
    last_context = None

    for warmup_cycle in range(1, int(max_warmup_cycles) + 1):
        try:
            context = collector.get_data()
            if context is None:
                skipped += 1
                print(f'[RC54.3.2 WARMUP] cycle={warmup_cycle}/{max_warmup_cycles} skipped=SOURCE_UNCHANGED_OR_INVALID')
            else:
                analyzable += 1
                context = pipeline.executar(context)
                last_context = context
                structure_trend = _enum_value(context.structure.trend)
                pa_bias = str(context.price_action.bias or 'NONE').strip().upper()
                ready = history_ready(context)
                trade_ready = context_ready(context)
                candle_count = int(getattr(context.market, 'candle_count', 0) or 0)
                print(
                    f'[RC54.3.2 WARMUP] cycle={warmup_cycle}/{max_warmup_cycles} '
                    f'analyzable={analyzable} candles={candle_count} '
                    f'structure={structure_trend} pa_bias={pa_bias} '
                    f'history_ready={ready} trade_context_ready={trade_ready}'
                )
                if ready and (not require_trade_context or trade_ready):
                    return {
                        'status': 'WARM_HISTORY_READY',
                        'ready': True,
                        'warmup_cycles': warmup_cycle,
                        'analyzable_samples': analyzable,
                        'skipped_cycles': skipped,
                        'errors': errors,
                        'structure_trend': structure_trend,
                        'pa_bias': pa_bias,
                        'trade_context_ready': trade_ready,
                        'trade_context_required': bool(require_trade_context),
                        'context': context,
                        'collector': collector,
                        'pipeline': pipeline,
                    }
        except Exception as exc:
            errors += 1
            print(f'[RC54.3.2 WARMUP] cycle={warmup_cycle}/{max_warmup_cycles} error={type(exc).__name__}:{exc}')

        if warmup_cycle < int(max_warmup_cycles) and float(interval) > 0:
            sleeper(float(interval))

    structure_trend = _enum_value(last_context.structure.trend) if last_context is not None else 'UNKNOWN'
    pa_bias = str(last_context.price_action.bias or 'NONE').strip().upper() if last_context is not None else 'NONE'
    last_history_ready = history_ready(last_context) if last_context is not None else False
    status = (
        'WARM_TRADE_CONTEXT_NOT_READY'
        if last_history_ready and require_trade_context
        else 'WARM_HISTORY_NOT_READY'
    )
    return {
        'status': status,
        'ready': False,
        'warmup_cycles': int(max_warmup_cycles),
        'analyzable_samples': analyzable,
        'skipped_cycles': skipped,
        'errors': errors,
        'structure_trend': structure_trend,
        'pa_bias': pa_bias,
        'trade_context_ready': context_ready(last_context) if last_context is not None else False,
        'trade_context_required': bool(require_trade_context),
        'context': last_context,
        'collector': collector,
        'pipeline': pipeline,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.3.2: aquece histórico até Market Structure + Price Action ficarem prontos.')
    p.add_argument('symbol')
    p.add_argument('--interval', type=float, default=0.25)
    p.add_argument('--max-warmup-cycles', type=int, default=4800)
    a = p.parse_args(argv)
    r = warm_history(a.symbol, interval=a.interval, max_warmup_cycles=a.max_warmup_cycles)
    print(f"PROFIT_RTD_RC54_3_2={r['status']}")
    for key in ('ready','warmup_cycles','analyzable_samples','skipped_cycles','errors','structure_trend','pa_bias'):
        print(f'{key}={r[key]}')
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('risk_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    return 0 if r['ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
