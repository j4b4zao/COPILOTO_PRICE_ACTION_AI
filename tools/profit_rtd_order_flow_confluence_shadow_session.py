from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from config.settings import EXCEL_PATH, ENABLE_ORDER_FLOW_SCORE
from connectors.excel_connector import ExcelConnector
from connectors.profit_reader import ProfitReader
from tools.profit_rtd_order_flow_combined_session import _build_sources
from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics
from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if ',' in text:
        text = text.replace('.', '').replace(',', '.')
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _read_price(reader: ProfitReader, symbol: str, attempts: int = 2):
    last_reason = 'PRICE_MISSING'
    for attempt in range(1, max(1, int(attempts)) + 1):
        quote = reader.obter_dados()
        quote_symbol = str(quote.get('ativo') or '').strip().upper()
        price = _to_float(quote.get('close'))
        if quote_symbol and quote_symbol != symbol:
            last_reason = 'SYMBOL_MISMATCH'
            continue
        if price is None:
            last_reason = 'PRICE_MISSING'
            continue
        return price, attempt, 'OK'
    return None, max(1, int(attempts)), last_reason


def run_session(symbol: str, *, cycles: int = 600, interval: float = 0.25, output_dir=None, sleeper=time.sleep):
    symbol = str(symbol or '').strip().upper()
    if not symbol:
        raise ValueError('symbol é obrigatório.')
    if ENABLE_ORDER_FLOW_SCORE:
        raise RuntimeError('ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED')
    if isinstance(cycles, bool) or int(cycles) < 1:
        raise ValueError('cycles deve ser inteiro >= 1.')
    if isinstance(interval, bool) or float(interval) < 0:
        raise ValueError('interval deve ser >= 0.')

    collector, book_provider = _build_sources()
    quote_excel = ExcelConnector()
    if not quote_excel.conectar(EXCEL_PATH):
        raise RuntimeError('Não foi possível conectar ao Profit.xlsx.')
    quote_reader = ProfitReader(quote_excel)

    delta_validator = ProfitDeltaQualityValidator()
    book_diag = BookDepthSourceDiagnostics()
    book_validator = BookDepthQualityValidator()
    builder = OrderFlowObservationalContextBuilder()

    samples = []
    collection_errors = 0
    missing_price_count = 0
    recovered_price_reads = 0
    alignment_counts = {'BULLISH_ALIGNED': 0, 'BEARISH_ALIGNED': 0, 'DIVERGENT': 0, 'NEUTRAL': 0}

    for cycle in range(1, int(cycles) + 1):
        try:
            collector.get_data()
            book = book_provider.snapshot(symbol)
            source_report = book_diag.observe(book)
            book_report = book_validator.evaluate(book, source_report)
            delta_report = delta_validator.evaluate(collector.order_flow)
            context = builder.build(delta_report=delta_report, book_report=book_report, symbol=symbol)
            last_price, attempts, price_reason = _read_price(quote_reader, symbol, attempts=2)
            if attempts > 1 and last_price is not None:
                recovered_price_reads += 1
            if last_price is None:
                missing_price_count += 1

            alignment = context.directional_alignment
            alignment_counts.setdefault(alignment, 0)
            alignment_counts[alignment] += 1
            samples.append({
                'cycle': cycle,
                'timestamp': datetime.now().isoformat(timespec='milliseconds'),
                'alignment': alignment,
                'confidence': context.confidence,
                'delta_status': context.delta_status,
                'book_status': context.book_status,
                'recent_delta': context.recent_delta,
                'dominance': context.delta_dominance,
                'persistence': context.delta_persistence,
                'acceleration': context.delta_acceleration,
                'imbalance': context.book_imbalance,
                'spread': context.book_spread,
                'last_price': last_price,
                'price_read_attempts': attempts,
                'price_read_reason': price_reason,
                'reasons': list(context.reasons),
            })
            print(
                f'[RC54 CONFLUENCE SHADOW] cycle={cycle}/{cycles} alignment={alignment} '
                f'delta={context.recent_delta:.2f} imbalance={context.book_imbalance:.4f} '
                f'last_price={last_price} attempts={attempts}'
            )
        except Exception as exc:
            collection_errors += 1
            print(f'[RC54 CONFLUENCE SHADOW] cycle={cycle}/{cycles} error={type(exc).__name__}:{exc}')

        if cycle < int(cycles) and float(interval) > 0:
            sleeper(float(interval))

    completed = len(samples)
    price_capture = completed == int(cycles) and missing_price_count == 0 and collection_errors == 0
    reasons = []
    if completed != int(cycles):
        reasons.append('INCOMPLETE_COLLECTION')
    if collection_errors:
        reasons.append('COLLECTION_ERRORS_PRESENT')
    if missing_price_count:
        reasons.append('MISSING_SYNCHRONIZED_LAST_PRICE')

    payload = {
        'status': 'COMPLETED' if not reasons else 'COMPLETED_WITH_WARNINGS',
        'phase': 'RC54.1_MICROSTRUCTURE_CONFLUENCE_BASELINE',
        'price_action_integration': 'PENDING_RC54_2',
        'symbol': symbol,
        'requested_cycles': int(cycles),
        'completed_cycles': completed,
        'alignment_counts': alignment_counts,
        'missing_price_count': missing_price_count,
        'recovered_price_reads': recovered_price_reads,
        'collection_errors': collection_errors,
        'price_capture': price_capture,
        'samples': samples,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
        'reasons': reasons,
    }

    target = Path(output_dir or r'C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_order_flow_confluence')
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = target / f'profit_rtd_order_flow_confluence_{symbol}_{stamp}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    payload['output_path'] = str(path)
    return payload


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.1 shadow: T&T + Book + preço sincronizado.')
    p.add_argument('symbol')
    p.add_argument('--cycles', type=int, default=600)
    p.add_argument('--interval', type=float, default=0.25)
    p.add_argument('--output-dir')
    a = p.parse_args(argv)
    r = run_session(a.symbol, cycles=a.cycles, interval=a.interval, output_dir=a.output_dir)
    print(f"PROFIT_RTD_RC54_1_CONFLUENCE_SHADOW={r['status']}")
    for key in ('symbol','requested_cycles','completed_cycles','missing_price_count','recovered_price_reads','collection_errors','price_capture','observational_only','predictive_claim_allowed','score_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    print('alignment_counts=' + json.dumps(r['alignment_counts'], sort_keys=True, separators=(',', ':')))
    print('reasons=' + ('|'.join(r['reasons']) if r['reasons'] else 'OK'))
    print(f"output_path={r['output_path']}")
    return 0 if r['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
