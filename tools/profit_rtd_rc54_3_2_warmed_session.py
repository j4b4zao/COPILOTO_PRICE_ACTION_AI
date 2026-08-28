from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics
from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator
from tools.profit_rtd_rc54_3_pa_structure_context_session import snapshot_context
from tools.profit_rtd_rc54_3_2_warm_history_gate import context_ready, warm_history


def run_warmed_session(symbol, *, cycles=600, interval=0.25, max_warmup_cycles=4800, output_dir=None, sleeper=time.sleep):
    symbol = str(symbol or '').strip().upper()
    if not symbol:
        raise ValueError('symbol é obrigatório.')
    if int(cycles) < 1 or int(max_warmup_cycles) < 1 or float(interval) < 0:
        raise ValueError('cycles/max_warmup_cycles/interval inválidos.')

    warm = warm_history(symbol, interval=interval, max_warmup_cycles=max_warmup_cycles, sleeper=sleeper)

    if not warm['ready']:
        return {
            'status': 'ABORTED_CONTEXT_NOT_READY', 'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
            'symbol': symbol, 'warmup': {k: v for k, v in warm.items() if k not in {'context','collector','pipeline'}},
            'requested_cycles': int(cycles), 'analyzable_samples': 0, 'skipped_cycles': 0, 'collection_errors': 0,
            'collection_error_details': [], 'missing_price_count': 0, 'price_capture': False,
            'data_ready': False, 'context_ready_at_start': False, 'trade_context_ready_at_end': False,
            'trade_context_ready_samples': 0, 'context_not_ready_samples': 0,
            'trade_context_reasons': ['WARM_HISTORY_NOT_READY'],
            'samples': [], 'observational_only': True,
            'predictive_claim_allowed': False, 'score_influence_allowed': False,
            'decision_influence_allowed': False, 'order_execution_allowed': False,
            'reasons': ['WARM_HISTORY_NOT_READY'],
        }

    collector = warm['collector']
    pipeline = warm['pipeline']
    delta_validator = ProfitDeltaQualityValidator()
    book_diag = BookDepthSourceDiagnostics()
    book_validator = BookDepthQualityValidator()
    builder = OrderFlowObservationalContextBuilder()

    samples = []
    skipped_cycles = 0
    collection_errors = 0
    collection_error_details = []
    missing_price_count = 0
    context_not_ready_samples = 0

    for cycle in range(1, int(cycles) + 1):
        try:
            context = collector.get_data()
            if context is None:
                skipped_cycles += 1
                print(f'[RC54.3.2] cycle={cycle}/{cycles} skipped=SOURCE_UNCHANGED_OR_INVALID')
            else:
                context = pipeline.executar(context)
                source_report = book_diag.observe(context.book_depth)
                book_report = book_validator.evaluate(context.book_depth, source_report)
                delta_report = delta_validator.evaluate(collector.order_flow)
                micro = builder.build(delta_report=delta_report, book_report=book_report, symbol=symbol)
                item = snapshot_context(context, micro)
                item['context_ready'] = context_ready(context)
                if not item['context_ready']:
                    context_not_ready_samples += 1
                if item['last_price'] is None:
                    missing_price_count += 1
                item['cycle'] = cycle
                item['timestamp'] = datetime.now().isoformat(timespec='milliseconds')
                samples.append(item)
                print(f"[RC54.3.2] cycle={cycle}/{cycles} alignment={item['alignment']} price={item['last_price']} structure={item['structure']['trend']} pa_bias={item['price_action']['bias']} ready={item['context_ready']}")
        except Exception as exc:
            collection_errors += 1
            detail = {'cycle': cycle, 'type': type(exc).__name__, 'message': str(exc)}
            collection_error_details.append(detail)
            print(f"[RC54.3.2] cycle={cycle}/{cycles} error={detail['type']}:{detail['message']}")

        if cycle < int(cycles) and float(interval) > 0:
            sleeper(float(interval))

    complete = len(samples) + skipped_cycles + collection_errors == int(cycles)
    # price_capture/data_ready describe synchronized market-data integrity only.
    # Trade-context readiness is reported independently because a valid SIDEWAYS/NONE
    # market state is not a data-source failure.
    price_capture = bool(samples) and missing_price_count == 0
    data_ready = complete and not collection_errors and price_capture
    trade_context_ready_samples = len(samples) - context_not_ready_samples
    trade_context_ready_at_end = bool(samples) and bool(samples[-1].get('context_ready', False))

    reasons = []
    if not complete:
        reasons.append('CYCLE_ACCOUNTING_MISMATCH')
    if collection_errors:
        reasons.append('COLLECTION_ERRORS_PRESENT')
    if missing_price_count:
        reasons.append('MISSING_SYNCHRONIZED_PRICE')
    if not samples:
        reasons.append('NO_ANALYZABLE_SAMPLES')

    trade_context_reasons = []
    if context_not_ready_samples:
        trade_context_reasons.append('CONTEXT_READINESS_DROPPED_DURING_SESSION')
    if samples and not trade_context_ready_at_end:
        trade_context_reasons.append('TRADE_CONTEXT_NOT_READY_AT_END')

    payload = {
        'status': 'COMPLETED' if not reasons else 'COMPLETED_WITH_WARNINGS',
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE', 'symbol': symbol,
        'warmup': {k: v for k, v in warm.items() if k not in {'context','collector','pipeline'}},
        'requested_cycles': int(cycles), 'analyzable_samples': len(samples), 'skipped_cycles': skipped_cycles,
        'collection_errors': collection_errors, 'collection_error_details': collection_error_details,
        'missing_price_count': missing_price_count, 'price_capture': price_capture, 'data_ready': data_ready,
        'context_ready_at_start': True, 'trade_context_ready_at_end': trade_context_ready_at_end,
        'trade_context_ready_samples': trade_context_ready_samples,
        'context_not_ready_samples': context_not_ready_samples,
        'trade_context_reasons': trade_context_reasons,
        'samples': samples, 'observational_only': True, 'predictive_claim_allowed': False,
        'score_influence_allowed': False, 'decision_influence_allowed': False, 'order_execution_allowed': False,
        'reasons': reasons,
    }

    target = Path(output_dir or r'C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_rc54_3_2')
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = target / f'profit_rtd_rc54_3_2_{symbol}_{stamp}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    payload['output_path'] = str(path)
    return payload


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.3.2: warm-up real seguido de 600 ciclos PA/Structure sincronizados.')
    p.add_argument('symbol')
    p.add_argument('--cycles', type=int, default=600)
    p.add_argument('--interval', type=float, default=0.25)
    p.add_argument('--max-warmup-cycles', type=int, default=4800)
    p.add_argument('--output-dir')
    a = p.parse_args(argv)
    r = run_warmed_session(a.symbol, cycles=a.cycles, interval=a.interval, max_warmup_cycles=a.max_warmup_cycles, output_dir=a.output_dir)
    print(f"PROFIT_RTD_RC54_3_2_WARMED_SESSION={r['status']}")
    print(f"symbol={r['symbol']}")
    print('warmup_status=' + r['warmup']['status'])
    print('warmup_cycles=' + str(r['warmup']['warmup_cycles']))
    print('context_ready_at_start=' + str(r['context_ready_at_start']))
    for key in ('requested_cycles','analyzable_samples','skipped_cycles','collection_errors','missing_price_count','price_capture','data_ready'):
        print(f'{key}={r[key]}')
    if 'trade_context_ready_at_end' in r:
        print(f"trade_context_ready_at_end={r['trade_context_ready_at_end']}")
    if 'trade_context_ready_samples' in r:
        print(f"trade_context_ready_samples={r['trade_context_ready_samples']}")
    if 'context_not_ready_samples' in r:
        print(f"context_not_ready_samples={r['context_not_ready_samples']}")
    if r.get('trade_context_reasons'):
        print('trade_context_reasons=' + '|'.join(r['trade_context_reasons']))
    else:
        print('trade_context_reasons=OK')
    if r.get('collection_error_details'):
        print('collection_error_details=' + json.dumps(r['collection_error_details'], ensure_ascii=False, separators=(',', ':')))
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    print('reasons=' + ('|'.join(r['reasons']) if r['reasons'] else 'OK'))
    if r.get('output_path'):
        print('output_path=' + r['output_path'])
    return 0 if r['status'] == 'COMPLETED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
