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


def data_ready(sample):
    return sample.get('last_price') is not None and str(sample.get('delta_status', '')).upper() in {'READY', 'VALID', 'LOW_ACTIVITY'}


def technical_reasons(*, complete, collection_errors, missing_price_count, samples, delta_failure_samples):
    reasons = []
    if not complete:
        reasons.append('CYCLE_ACCOUNTING_MISMATCH')
    if collection_errors:
        reasons.append('COLLECTION_ERRORS_PRESENT')
    if missing_price_count:
        reasons.append('MISSING_SYNCHRONIZED_PRICE')
    if not samples:
        reasons.append('NO_ANALYZABLE_SAMPLES')
    if delta_failure_samples:
        reasons.append('DELTA_NOT_READY_OR_INVALID')
    return reasons


def run_warmed_session(symbol, *, cycles=600, interval=0.25, max_warmup_cycles=4800, require_trade_context_at_start=False, output_dir=None, sleeper=time.sleep):
    symbol = str(symbol or '').strip().upper()
    if not symbol:
        raise ValueError('symbol é obrigatório.')
    if int(cycles) < 1 or int(max_warmup_cycles) < 1 or float(interval) < 0:
        raise ValueError('cycles/max_warmup_cycles/interval inválidos.')

    warm = warm_history(symbol, interval=interval, max_warmup_cycles=max_warmup_cycles, require_trade_context=require_trade_context_at_start, sleeper=sleeper)

    if not warm['ready']:
        return {
            'status': 'ABORTED_CONTEXT_NOT_READY', 'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
            'symbol': symbol, 'warmup': {k: v for k, v in warm.items() if k not in {'context','collector','pipeline'}},
            'requested_cycles': int(cycles), 'analyzable_samples': 0, 'skipped_cycles': 0, 'collection_errors': 0,
            'collection_error_details': [], 'missing_price_count': 0, 'price_capture': False,
            'data_ready': False, 'trade_context_ready': False,
            'trade_context_ready_at_start': False, 'context_ready_at_start': False,
            'samples': [], 'observational_only': True,
            'predictive_claim_allowed': False, 'score_influence_allowed': False, 'risk_influence_allowed': False,
            'decision_influence_allowed': False, 'order_execution_allowed': False,
            'reasons': [str(warm.get('status') or 'WARM_HISTORY_NOT_READY')],
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
    delta_not_ready_samples = 0
    delta_failure_samples = 0

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
                item['data_ready'] = data_ready(item)
                item['trade_context_ready'] = context_ready(context)
                # Kept for consumers of RC54.3.2 session files.
                item['context_ready'] = item['trade_context_ready']
                if not item['trade_context_ready']:
                    context_not_ready_samples += 1
                delta_status = str(item.get('delta_status', '')).upper()
                if delta_status not in {'READY', 'VALID', 'LOW_ACTIVITY'}:
                    delta_not_ready_samples += 1
                if delta_status not in {'READY', 'VALID', 'LOW_ACTIVITY', 'INITIALIZING'}:
                    delta_failure_samples += 1
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
    # price_capture describes synchronized price availability in captured samples only.
    # A collection exception is reported independently and must not erase valid price evidence.
    price_capture = bool(samples) and missing_price_count == 0
    reasons = technical_reasons(
        complete=complete, collection_errors=collection_errors,
        missing_price_count=missing_price_count, samples=samples,
        delta_failure_samples=delta_failure_samples,
    )
    session_data_ready = not reasons
    trade_context_ready = bool(samples) and bool(samples[-1]['trade_context_ready'])

    payload = {
        'status': 'COMPLETED' if not reasons else 'COMPLETED_WITH_WARNINGS',
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE', 'symbol': symbol,
        'warmup': {k: v for k, v in warm.items() if k not in {'context','collector','pipeline'}},
        'requested_cycles': int(cycles), 'analyzable_samples': len(samples), 'skipped_cycles': skipped_cycles,
        'collection_errors': collection_errors, 'collection_error_details': collection_error_details,
        'missing_price_count': missing_price_count, 'price_capture': price_capture,
        'data_ready': session_data_ready, 'delta_not_ready_samples': delta_not_ready_samples,
        'delta_failure_samples': delta_failure_samples,
        'trade_context_ready': trade_context_ready,
        'trade_context_ready_at_start': bool(warm.get('trade_context_ready', True)),
        'context_ready_at_start': bool(warm.get('trade_context_ready', True)),
        'context_not_ready_samples': context_not_ready_samples,
        'samples': samples, 'observational_only': True, 'predictive_claim_allowed': False,
        'score_influence_allowed': False, 'risk_influence_allowed': False, 'decision_influence_allowed': False, 'order_execution_allowed': False,
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
    print('trade_context_ready_at_start=' + str(r['trade_context_ready_at_start']))
    print('context_ready_at_start=' + str(r['context_ready_at_start']))
    for key in ('requested_cycles','analyzable_samples','skipped_cycles','collection_errors','missing_price_count','price_capture'):
        print(f'{key}={r[key]}')
    if 'context_not_ready_samples' in r:
        print(f"context_not_ready_samples={r['context_not_ready_samples']}")
    for key in ('data_ready','delta_not_ready_samples','delta_failure_samples','trade_context_ready'):
        if key in r:
            print(f'{key}={r[key]}')
    if r.get('collection_error_details'):
        print('collection_error_details=' + json.dumps(r['collection_error_details'], ensure_ascii=False, separators=(',', ':')))
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('risk_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    print('reasons=' + ('|'.join(r['reasons']) if r['reasons'] else 'OK'))
    if r.get('output_path'):
        print('output_path=' + r['output_path'])
    return 0 if r['status'] == 'COMPLETED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
