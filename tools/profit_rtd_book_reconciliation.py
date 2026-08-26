"""RC39/RC53.1 - reconciliação Excel RTD x WorkbookReader x Book Snapshot.

Congela uma única matriz A1:H52 por ciclo e compara as quantidades brutas
Compra/Venda com o payload do ProfitRTDBookDepthReader e o BookDepthSnapshot.
RC53.1 também captura o preço Último real do Profit.xlsx no mesmo ciclo,
sem usar proxy e sem alterar Score, Decision ou execução.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

from config.settings import ENABLE_ORDER_FLOW_SCORE, EXCEL_PATH, PROFIT_RTD_ORDER_BOOK_PATH
from connectors.excel_connector import ExcelConnector
from market_data.book_depth_level2_provider import NormalizedLevel2BookDepthProvider
from market_data.excel_range_gateway import ExcelRangeGateway
from market_data.profit_rtd_workbook_reader import ProfitRTDBookDepthReader

MAX_CYCLES = 3600
TOLERANCE = 1e-9


class FrozenMatrixGateway:
    """Gateway imutável para garantir que Reader e Snapshot usem a mesma matriz."""

    def __init__(self, matrix):
        self.matrix = [list(row) for row in matrix]

    def read_range(self, sheet: str, cell_range: str):
        return [list(row) for row in self.matrix]


def _number(value):
    if isinstance(value, bool):
        raise TypeError("valor booleano não é quantidade válida")
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value or "").strip()
        if not text:
            raise ValueError("quantidade vazia")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        number = float(text)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("quantidade deve ser positiva e finita")
    return number


def _price_number(value):
    if isinstance(value, bool):
        raise TypeError("preço booleano inválido")
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value or "").strip()
        if not text:
            raise ValueError("preço vazio")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        number = float(text)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("preço deve ser positivo e finito")
    return number


def _raw_totals(matrix):
    if not isinstance(matrix, (list, tuple)) or len(matrix) < 3:
        raise ValueError("matriz RTD inválida")
    rows = [list(row) for row in matrix]
    if any(len(row) < 8 for row in rows):
        raise ValueError("matriz RTD incompleta")
    bid = ask = 0.0
    levels = 0
    for row in rows[2:]:
        if all(str(value or "").strip() == "" for value in row[:8]):
            continue
        bid += _number(row[2])
        ask += _number(row[5])
        levels += 1
    if levels == 0:
        raise ValueError("Book RTD sem níveis")
    total = bid + ask
    imbalance = (bid - ask) / total if total > 0 else 0.0
    return bid, ask, imbalance, levels


def _close(a, b):
    return abs(float(a) - float(b)) <= TOLERANCE


def _build_excel_gateway():
    excel = ExcelConnector()
    if not excel.conectar(PROFIT_RTD_ORDER_BOOK_PATH):
        raise RuntimeError("Não foi possível conectar ao Livro de Ofertas RTD.")
    return ExcelRangeGateway(excel), excel


def _build_price_excel():
    excel = ExcelConnector()
    if not excel.conectar(EXCEL_PATH):
        raise RuntimeError("Não foi possível conectar ao Profit.xlsx para capturar o preço.")
    return excel


def _read_last_price(price_excel, symbol):
    observed_symbol = str(price_excel.ler_celula("Planilha1", "A2") or "").strip().upper()
    if observed_symbol and observed_symbol != symbol:
        raise ValueError(f"PRICE_SYMBOL_MISMATCH:{observed_symbol}!={symbol}")
    return _price_number(price_excel.ler_celula("Planilha1", "D2"))


def reconcile_matrix(matrix, symbol):
    raw_bid, raw_ask, raw_imbalance, raw_levels = _raw_totals(matrix)
    frozen = FrozenMatrixGateway(matrix)
    reader = ProfitRTDBookDepthReader(frozen)
    payload = reader.read_book_depth(symbol)
    reader_bid = sum(float(level["quantity"]) for level in payload["bids"])
    reader_ask = sum(float(level["quantity"]) for level in payload["asks"])

    snapshot = NormalizedLevel2BookDepthProvider(reader, source="PROFIT_RTD", max_levels=50).snapshot(symbol)
    if not snapshot.available:
        raise ValueError("BOOK_SNAPSHOT_UNAVAILABLE")

    snap_bid = float(snapshot.bid_quantity)
    snap_ask = float(snapshot.ask_quantity)
    snap_imbalance = float(snapshot.imbalance)
    expected_imbalance = round(raw_imbalance, 6)
    matches = {
        "raw_reader_bid": _close(raw_bid, reader_bid),
        "raw_reader_ask": _close(raw_ask, reader_ask),
        "reader_snapshot_bid": _close(reader_bid, snap_bid),
        "reader_snapshot_ask": _close(reader_ask, snap_ask),
        "raw_snapshot_imbalance": _close(expected_imbalance, snap_imbalance),
        "levels": raw_levels == len(payload["bids"]) == len(payload["asks"]) == len(snapshot.bids) == len(snapshot.asks),
    }
    return {
        "raw_bid_quantity": raw_bid,
        "raw_ask_quantity": raw_ask,
        "raw_imbalance": expected_imbalance,
        "reader_bid_quantity": reader_bid,
        "reader_ask_quantity": reader_ask,
        "snapshot_bid_quantity": snap_bid,
        "snapshot_ask_quantity": snap_ask,
        "snapshot_imbalance": snap_imbalance,
        "levels": raw_levels,
        "best_bid": snapshot.best_bid,
        "best_ask": snapshot.best_ask,
        "matches": matches,
        "all_match": all(matches.values()),
    }


def run(symbol, *, cycles, interval, output_dir, execute=False, sleeper=time.sleep):
    if not execute:
        print("PROFIT_RTD_BOOK_RECONCILIATION=NOT_STARTED")
        print("reason=EXECUTE_FLAG_REQUIRED")
        return 2
    if ENABLE_ORDER_FLOW_SCORE:
        print("PROFIT_RTD_BOOK_RECONCILIATION=NOT_STARTED")
        print("reason=ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED")
        return 2
    if not (1 <= int(cycles) <= MAX_CYCLES) or float(interval) < 0:
        print("PROFIT_RTD_BOOK_RECONCILIATION=NOT_STARTED")
        print("reason=INVALID_CYCLES_OR_INTERVAL")
        return 2

    symbol = str(symbol or "").strip().upper()
    target = Path(output_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    try:
        gateway, book_excel = _build_excel_gateway()
        price_excel = _build_price_excel()
    except Exception as exc:
        print("PROFIT_RTD_BOOK_RECONCILIATION=ERROR")
        print(f"reason=BOOTSTRAP_ERROR:{type(exc).__name__}:{exc}")
        return 1

    samples = []
    errors = 0
    mismatch_cycles = 0
    negative_raw = 0
    positive_raw = 0
    missing_price = 0
    for cycle in range(1, int(cycles) + 1):
        try:
            matrix = gateway.read_range("Planilha1", "A1:H52")
            last_price = _read_last_price(price_excel, symbol)
            result = reconcile_matrix(matrix, symbol)
            result["cycle"] = cycle
            result["timestamp"] = datetime.now().isoformat(timespec="milliseconds")
            result["last_price"] = last_price
            samples.append(result)
            mismatch_cycles += not result["all_match"]
            positive_raw += result["raw_imbalance"] > 0
            negative_raw += result["raw_imbalance"] < 0
            print(
                f"[BOOK RECON] cycle={cycle}/{cycles} raw_bid={result['raw_bid_quantity']:.2f} "
                f"raw_ask={result['raw_ask_quantity']:.2f} raw_imb={result['raw_imbalance']:.6f} "
                f"snap_imb={result['snapshot_imbalance']:.6f} last_price={last_price:.2f} "
                f"match={result['all_match']}"
            )
        except Exception as exc:
            errors += 1
            if "preço" in str(exc).lower() or "PRICE_" in str(exc):
                missing_price += 1
            print(f"[BOOK RECON] cycle={cycle}/{cycles} error={type(exc).__name__}:{exc}")
        if cycle < int(cycles) and float(interval) > 0:
            sleeper(float(interval))

    completed = len(samples)
    status = "COMPLETED" if completed == int(cycles) and errors == 0 else "COMPLETED_WITH_WARNINGS"
    reasons = []
    if mismatch_cycles:
        reasons.append("EXCEL_READER_SNAPSHOT_MISMATCH")
    if negative_raw == 0 and completed:
        reasons.append("NO_NEGATIVE_RAW_IMBALANCE_OBSERVED")
    if missing_price:
        reasons.append("MISSING_SYNCHRONIZED_LAST_PRICE")
    if errors:
        reasons.append("COLLECTION_ERRORS_OR_SKIPPED_CYCLES")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target / f"profit_rtd_book_reconciliation_{symbol}_{stamp}.json"
    payload = {
        "status": status,
        "symbol": symbol,
        "requested_cycles": int(cycles),
        "completed_cycles": completed,
        "mismatch_cycles": int(mismatch_cycles),
        "positive_raw_imbalance_count": int(positive_raw),
        "negative_raw_imbalance_count": int(negative_raw),
        "price_capture": completed > 0 and missing_price == 0,
        "missing_price_count": int(missing_price),
        "collection_errors": errors,
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
        "reasons": reasons,
        "samples": samples,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PROFIT_RTD_BOOK_RECONCILIATION={status}")
    print(f"symbol={symbol}")
    print(f"completed_cycles={completed}")
    print(f"mismatch_cycles={mismatch_cycles}")
    print(f"positive_raw_imbalance_count={positive_raw}")
    print(f"negative_raw_imbalance_count={negative_raw}")
    print(f"price_capture={completed > 0 and missing_price == 0}")
    print(f"missing_price_count={missing_price}")
    print(f"collection_errors={errors}")
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    print("reasons=" + ("|".join(reasons) if reasons else "OK"))
    print(f"output_path={path}")
    return 0 if status == "COMPLETED" else 1


def main(argv=None):
    p = argparse.ArgumentParser(description="Reconcilia Excel RTD, WorkbookReader e Book Snapshot com captura de preço.")
    p.add_argument("symbol")
    p.add_argument("--cycles", required=True, type=int)
    p.add_argument("--interval", type=float, default=0.25)
    p.add_argument("--output-dir", default=r"C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_book_reconciliation")
    p.add_argument("--execute", action="store_true")
    a = p.parse_args(argv)
    return run(a.symbol, cycles=a.cycles, interval=a.interval, output_dir=a.output_dir, execute=a.execute)


if __name__ == "__main__":
    sys.exit(main())
