from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from config.settings import EXCEL_PATH, PROFIT_RTD_ORDER_BOOK_PATH
from connectors.excel_connector import ExcelConnector
from connectors.profit_reader import ProfitReader
from market_data.book_depth_level2_provider import NormalizedLevel2BookDepthProvider
from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics
from market_data.excel_range_gateway import ExcelRangeGateway
from market_data.profit_rtd_workbook_reader import ProfitRTDBookDepthReader


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip().replace('.', '').replace(',', '.') if ',' in str(value) else str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _sample(snapshot, source, quality, last_price, cycle):
    return {
        'cycle': int(cycle),
        'symbol': str(getattr(source, 'symbol', '') or ''),
        'source_status': str(getattr(source, 'status', 'NO_DATA') or 'NO_DATA'),
        'quality_status': str(getattr(quality, 'status', 'NO_DATA') or 'NO_DATA'),
        'bid_levels': int(getattr(quality, 'levels_bid', 0) or 0),
        'ask_levels': int(getattr(quality, 'levels_ask', 0) or 0),
        'spread': float(getattr(quality, 'spread', 0.0) or 0.0),
        'imbalance': float(getattr(quality, 'imbalance', 0.0) or 0.0),
        'last_price': last_price,
        'available': bool(getattr(snapshot, 'available', False)),
        'anomaly_count': int(getattr(quality, 'anomaly_count', 0) or 0),
        'passive_only': True,
    }


def run_session(symbol: str, *, cycles: int = 600, interval: float = 0.25, output_dir=None, sleeper=time.sleep):
    symbol = str(symbol or '').strip().upper()
    if not symbol:
        raise ValueError('symbol é obrigatório.')
    if isinstance(cycles, bool) or int(cycles) < 1:
        raise ValueError('cycles deve ser inteiro >= 1.')
    if isinstance(interval, bool) or float(interval) < 0:
        raise ValueError('interval deve ser >= 0.')

    book_excel = ExcelConnector()
    quote_excel = ExcelConnector()
    if not book_excel.conectar(PROFIT_RTD_ORDER_BOOK_PATH):
        raise RuntimeError('Não foi possível conectar ao livro RTD.')
    if not quote_excel.conectar(EXCEL_PATH):
        raise RuntimeError('Não foi possível conectar ao Profit.xlsx.')

    gateway = ExcelRangeGateway(book_excel)
    reader = ProfitRTDBookDepthReader(gateway)
    provider = NormalizedLevel2BookDepthProvider(reader, source='PROFIT_RTD', max_levels=50)
    diagnostics = BookDepthSourceDiagnostics()
    validator = BookDepthQualityValidator()
    quote_reader = ProfitReader(quote_excel)

    rows = []
    collection_errors = 0
    missing_price_count = 0

    for cycle in range(1, int(cycles) + 1):
        try:
            snapshot = provider.snapshot(symbol)
            source = diagnostics.observe(snapshot)
            quality = validator.evaluate(snapshot, source)
            quote = quote_reader.obter_dados()
            quote_symbol = str(quote.get('ativo') or '').strip().upper()
            last_price = _to_float(quote.get('close'))
            if quote_symbol and quote_symbol != symbol:
                last_price = None
            if last_price is None:
                missing_price_count += 1
            rows.append(_sample(snapshot, source, quality, last_price, cycle))
            print(
                '[BOOK EXT SYNC] '
                f'cycle={cycle}/{cycles} quality={quality.status} '
                f'imbalance={float(getattr(quality, "imbalance", 0.0) or 0.0):.4f} '
                f'last_price={last_price}'
            )
        except Exception as exc:
            collection_errors += 1
            print(f'[BOOK EXT SYNC] cycle={cycle}/{cycles} error={type(exc).__name__}:{exc}')

        if cycle < int(cycles) and interval > 0:
            sleeper(float(interval))

    completed = len(rows)
    price_capture = completed == int(cycles) and missing_price_count == 0 and collection_errors == 0
    reasons = []
    if completed != int(cycles): reasons.append('INCOMPLETE_COLLECTION')
    if collection_errors: reasons.append('COLLECTION_ERRORS_PRESENT')
    if missing_price_count: reasons.append('MISSING_SYNCHRONIZED_LAST_PRICE')

    result = {
        'status': 'COMPLETED' if not reasons else 'COMPLETED_WITH_WARNINGS',
        'symbol': symbol,
        'requested_cycles': int(cycles),
        'completed_cycles': completed,
        'missing_price_count': missing_price_count,
        'collection_errors': collection_errors,
        'price_capture': price_capture,
        'samples': rows,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
        'reasons': reasons,
    }

    target_dir = Path(output_dir or r'C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_book_reconciliation')
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = target_dir / f'profit_rtd_book_reconciliation_{symbol}_{stamp}.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    result['output_path'] = str(path)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description='Sessão estendida Book RTD + preço sincronizado.')
    p.add_argument('symbol')
    p.add_argument('--cycles', type=int, default=600)
    p.add_argument('--interval', type=float, default=0.25)
    p.add_argument('--output-dir')
    a = p.parse_args(argv)
    r = run_session(a.symbol, cycles=a.cycles, interval=a.interval, output_dir=a.output_dir)
    print(f"PROFIT_RTD_BOOK_EXTENDED_SYNCHRONIZED_SESSION={r['status']}")
    for key in ('symbol','requested_cycles','completed_cycles','missing_price_count','collection_errors','price_capture','observational_only','predictive_claim_allowed','score_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    print('reasons=' + ('|'.join(r['reasons']) if r['reasons'] else 'OK'))
    print(f"output_path={r['output_path']}")
    return 0 if r['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
