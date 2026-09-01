from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from analysis.analysis_pipeline import AnalysisPipeline
from config.settings import ENABLE_ORDER_FLOW_SCORE
from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics
from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator
from tools.profit_rtd_order_flow_combined_session import _build_sources


def _enum_value(value):
    return str(getattr(value, 'value', value))


def _last_price(context):
    candle = getattr(context.market, 'last_candle', None)
    if candle is None:
        return None
    value = getattr(candle, 'close', None)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def snapshot_context(context, micro):
    structure = context.structure
    pa = context.price_action
    return {
        'alignment': micro.directional_alignment,
        'confidence': micro.confidence,
        'delta_status': micro.delta_status,
        'book_status': micro.book_status,
        'recent_delta': micro.recent_delta,
        'dominance': micro.delta_dominance,
        'persistence': micro.delta_persistence,
        'acceleration': micro.delta_acceleration,
        'imbalance': micro.book_imbalance,
        'spread': micro.book_spread,
        'last_price': _last_price(context),
        'structure': {
            'valid': bool(getattr(structure, 'valid', False)),
            'trend': _enum_value(structure.trend),
            'hh': bool(structure.hh),
            'hl': bool(structure.hl),
            'lh': bool(structure.lh),
            'll': bool(structure.ll),
            'bos_up': bool(structure.bos_up),
            'bos_down': bool(structure.bos_down),
            'choch': bool(structure.choch),
            'last_high': float(structure.last_high or 0.0),
            'last_low': float(structure.last_low or 0.0),
            'score': float(structure.score or 0.0),
            'confluences': int(structure.confluences or 0),
        },
        'price_action': {
            'trend': _enum_value(pa.trend),
            'bias': str(pa.bias or 'NONE'),
            'structure': str(pa.structure or ''),
            'bos': bool(pa.bos),
            'choch': bool(pa.choch),
            'bullish_engulfing': bool(pa.bullish_engulfing),
            'bearish_engulfing': bool(pa.bearish_engulfing),
            'hammer': bool(pa.hammer),
            'shooting_star': bool(pa.shooting_star),
            'doji': bool(pa.doji),
            'inside_bar': bool(pa.inside_bar),
            'outside_bar': bool(pa.outside_bar),
            'bar_classification': str(pa.bar_classification or 'UNKNOWN'),
            'bar_direction': str(pa.bar_direction or 'NONE'),
            'trend_bar_strength': str(pa.trend_bar_strength or 'UNKNOWN'),
            'brooks_breakout_phase': str(pa.brooks_breakout_phase or 'UNKNOWN'),
            'brooks_breakout_direction': str(pa.brooks_breakout_direction or 'NONE'),
            'brooks_breakout_follow_through': bool(pa.brooks_breakout_follow_through),
            'brooks_breakout_failed': bool(pa.brooks_breakout_failed),
            'brooks_signal_phase': str(pa.brooks_signal_phase or 'UNKNOWN'),
            'brooks_signal_direction': str(pa.brooks_signal_direction or 'NONE'),
            'brooks_signal_quality': str(pa.brooks_signal_quality or 'UNKNOWN'),
            'brooks_signal_context': str(pa.brooks_signal_context or 'NEUTRAL'),
            'brooks_entry_triggered': bool(pa.brooks_entry_triggered),
            'brooks_follow_through': bool(pa.brooks_follow_through),
            'brooks_reversal_candidate': bool(pa.brooks_reversal_candidate),
            'brooks_reversal_direction': str(pa.brooks_reversal_direction or 'NONE'),
            'brooks_reversal_quality': str(pa.brooks_reversal_quality or 'NONE'),
            'brooks_composite_pattern': str(pa.brooks_composite_pattern or 'NONE'),
            'brooks_composite_direction': str(pa.brooks_composite_direction or 'NONE'),
        },
    }


def run_session(symbol, *, cycles=600, interval=0.25, output_dir=None, sleeper=time.sleep):
    symbol = str(symbol or '').strip().upper()
    if not symbol:
        raise ValueError('symbol é obrigatório.')
    if ENABLE_ORDER_FLOW_SCORE:
        raise RuntimeError('ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED')
    if int(cycles) < 1 or float(interval) < 0:
        raise ValueError('cycles/interval inválidos.')

    collector, book_provider = _build_sources()
    pipeline = AnalysisPipeline(book_depth_service=book_provider)
    delta_validator = ProfitDeltaQualityValidator()
    book_diag = BookDepthSourceDiagnostics()
    book_validator = BookDepthQualityValidator()
    builder = OrderFlowObservationalContextBuilder()

    samples = []
    collection_errors = 0
    skipped_cycles = 0
    missing_price_count = 0

    for cycle in range(1, int(cycles) + 1):
        try:
            context = collector.get_data()
            if context is None:
                skipped_cycles += 1
                print(f'[RC54.3] cycle={cycle}/{cycles} skipped=SOURCE_UNCHANGED_OR_INVALID')
            else:
                context = pipeline.executar(context)
                source_report = book_diag.observe(context.book_depth)
                book_report = book_validator.evaluate(context.book_depth, source_report)
                delta_report = delta_validator.evaluate(collector.order_flow)
                micro = builder.build(delta_report=delta_report, book_report=book_report, symbol=symbol)
                item = snapshot_context(context, micro)
                if item['last_price'] is None:
                    missing_price_count += 1
                item['cycle'] = cycle
                item['timestamp'] = datetime.now().isoformat(timespec='milliseconds')
                samples.append(item)
                print(
                    f"[RC54.3] cycle={cycle}/{cycles} alignment={item['alignment']} "
                    f"price={item['last_price']} structure={item['structure']['trend']} "
                    f"pa_bias={item['price_action']['bias']}"
                )
        except Exception as exc:
            collection_errors += 1
            print(f'[RC54.3] cycle={cycle}/{cycles} error={type(exc).__name__}:{exc}')
        if cycle < int(cycles) and float(interval) > 0:
            sleeper(float(interval))

    complete = len(samples) + skipped_cycles + collection_errors == int(cycles)
    price_capture = bool(samples) and missing_price_count == 0 and collection_errors == 0
    reasons = []
    if not complete:
        reasons.append('CYCLE_ACCOUNTING_MISMATCH')
    if collection_errors:
        reasons.append('COLLECTION_ERRORS_PRESENT')
    if missing_price_count:
        reasons.append('MISSING_SYNCHRONIZED_PRICE')
    if not samples:
        reasons.append('NO_ANALYZABLE_SAMPLES')

    payload = {
        'status': 'COMPLETED' if not reasons else 'COMPLETED_WITH_WARNINGS',
        'phase': 'RC54.3_SYNCHRONIZED_PA_STRUCTURE_CONTEXT_CAPTURE',
        'symbol': symbol,
        'requested_cycles': int(cycles),
        'analyzable_samples': len(samples),
        'skipped_cycles': skipped_cycles,
        'collection_errors': collection_errors,
        'missing_price_count': missing_price_count,
        'price_capture': price_capture,
        'samples': samples,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
        'reasons': reasons,
    }
    target = Path(output_dir or r'C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_rc54_3')
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = target / f'profit_rtd_rc54_3_{symbol}_{stamp}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    payload['output_path'] = str(path)
    return payload


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.3 shadow: T&T + Book + preço + PA/Structure sincronizados.')
    p.add_argument('symbol')
    p.add_argument('--cycles', type=int, default=600)
    p.add_argument('--interval', type=float, default=0.25)
    p.add_argument('--output-dir')
    a = p.parse_args(argv)
    r = run_session(a.symbol, cycles=a.cycles, interval=a.interval, output_dir=a.output_dir)
    print(f"PROFIT_RTD_RC54_3={r['status']}")
    for key in ('symbol','requested_cycles','analyzable_samples','skipped_cycles','collection_errors','missing_price_count','price_capture','observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    print('reasons=' + ('|'.join(r['reasons']) if r['reasons'] else 'OK'))
    print(f"output_path={r['output_path']}")
    return 0 if r['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
