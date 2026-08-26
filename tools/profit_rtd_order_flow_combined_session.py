"""Sessao real observacional combinada de T&T + Book RTD (RC30)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from datetime import datetime

from config.settings import (
    ENABLE_ORDER_FLOW_SCORE,
    PROFIT_RTD_ORDER_BOOK_PATH,
    PROFIT_RTD_TIMES_TRADES_PATH,
)
from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics
from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator

MAX_CYCLES = 3600


def build_parser():
    p = argparse.ArgumentParser(description="Valida T&T + Book RTD em conjunto, sem efeito operacional.")
    p.add_argument("symbol")
    p.add_argument("--cycles", required=True, type=int)
    p.add_argument("--interval", type=float, default=0.25)
    p.add_argument("--output-dir", default=r"C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_order_flow_combined")
    p.add_argument("--execute", action="store_true")
    return p


def _build_sources():
    from connectors.excel_connector import ExcelConnector
    from market_data.collector import Collector
    from market_data.excel_range_gateway import ExcelRangeGateway
    from market_data.profit_rtd_book_depth_reader import ProfitRTDBookDepthReader
    from market_data.profit_rtd_order_flow_pipeline import ProfitRTDOrderFlowPipeline
    from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader

    collector = Collector(enable_profit_rtd_order_flow=False)

    tt_excel = ExcelConnector()
    if not tt_excel.conectar(PROFIT_RTD_TIMES_TRADES_PATH):
        raise RuntimeError("Nao foi possivel conectar ao Times & Trades RTD.")
    tt_reader = ProfitRTDTimesTradesReader(ExcelRangeGateway(tt_excel))
    collector.profit_rtd_order_flow_pipeline = ProfitRTDOrderFlowPipeline(tt_reader, collector.order_flow)
    collector.enable_profit_rtd_order_flow = True
    collector.profit_rtd_times_trades_excel = tt_excel

    book_excel = ExcelConnector()
    if not book_excel.conectar(PROFIT_RTD_ORDER_BOOK_PATH):
        raise RuntimeError("Nao foi possivel conectar ao Livro de Ofertas RTD.")
    book_reader = ProfitRTDBookDepthReader(ExcelRangeGateway(book_excel))
    return collector, book_reader


def run(symbol, *, cycles, interval, output_dir, execute=False):
    if not execute:
        print("PROFIT_RTD_ORDER_FLOW_COMBINED=NOT_STARTED")
        print("reason=EXECUTE_FLAG_REQUIRED")
        return 2
    if ENABLE_ORDER_FLOW_SCORE:
        print("PROFIT_RTD_ORDER_FLOW_COMBINED=NOT_STARTED")
        print("reason=ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED")
        return 2
    if not (1 <= int(cycles) <= MAX_CYCLES) or float(interval) < 0:
        print("PROFIT_RTD_ORDER_FLOW_COMBINED=NOT_STARTED")
        print("reason=INVALID_CYCLES_OR_INTERVAL")
        return 2

    symbol = str(symbol or "").upper()
    target = Path(output_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    try:
        collector, book_reader = _build_sources()
    except Exception as exc:
        print("PROFIT_RTD_ORDER_FLOW_COMBINED=ERROR")
        print(f"reason=BOOTSTRAP_ERROR:{type(exc).__name__}:{exc}")
        return 1

    delta_validator = ProfitDeltaQualityValidator()
    book_diag = BookDepthSourceDiagnostics()
    book_validator = BookDepthQualityValidator()
    builder = OrderFlowObservationalContextBuilder()

    samples = []
    align_counts = {"BULLISH_ALIGNED": 0, "BEARISH_ALIGNED": 0, "DIVERGENT": 0, "NEUTRAL": 0}
    alignment_changes = 0
    collection_errors = 0
    last_alignment = None

    for cycle in range(1, int(cycles) + 1):
        try:
            market = collector.get_data()
            book = book_reader.read(symbol)
            source_report = book_diag.observe(book)
            book_report = book_validator.evaluate(book, source_report)
            delta_report = delta_validator.evaluate(collector.order_flow)
            context = builder.build(delta_report=delta_report, book_report=book_report, symbol=symbol)
        except Exception as exc:
            collection_errors += 1
            print(f"[ORDER FLOW COMBINED] cycle={cycle}/{cycles} error={type(exc).__name__}:{exc}")
            time.sleep(float(interval))
            continue

        alignment = context.directional_alignment
        align_counts.setdefault(alignment, 0)
        align_counts[alignment] += 1
        if last_alignment is not None and alignment != last_alignment:
            alignment_changes += 1
        last_alignment = alignment

        samples.append({
            "cycle": cycle,
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "status": context.status,
            "alignment": alignment,
            "confidence": context.confidence,
            "delta_status": context.delta_status,
            "book_status": context.book_status,
            "recent_delta": context.recent_delta,
            "dominance": context.delta_dominance,
            "persistence": context.delta_persistence,
            "acceleration": context.delta_acceleration,
            "imbalance": context.book_imbalance,
            "spread": context.book_spread,
            "reasons": list(context.reasons),
        })
        print(
            f"[ORDER FLOW COMBINED] cycle={cycle}/{cycles} status={context.status} "
            f"alignment={alignment} confidence={context.confidence:.4f} "
            f"delta_status={context.delta_status} book_status={context.book_status} "
            f"delta={context.recent_delta:.2f} dominance={context.delta_dominance:.4f} "
            f"imbalance={context.book_imbalance:.4f} spread={context.book_spread:.2f}"
        )
        time.sleep(float(interval))

    completed = len(samples)
    status = "COMPLETED" if completed == int(cycles) and collection_errors == 0 else "COMPLETED_WITH_WARNINGS"
    reasons = [] if status == "COMPLETED" else ["COLLECTION_ERRORS_OR_SKIPPED_CYCLES"]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target / f"profit_rtd_order_flow_combined_{symbol}_{stamp}.json"
    payload = {
        "status": status,
        "symbol": symbol,
        "requested_cycles": int(cycles),
        "completed_cycles": completed,
        "alignment_counts": align_counts,
        "alignment_changes": alignment_changes,
        "collection_errors": collection_errors,
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
        "reasons": reasons,
        "samples": samples,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PROFIT_RTD_ORDER_FLOW_COMBINED={status}")
    print(f"symbol={symbol}")
    print(f"requested_cycles={cycles}")
    print(f"completed_cycles={completed}")
    print(f"bullish_aligned={align_counts.get('BULLISH_ALIGNED', 0)}")
    print(f"bearish_aligned={align_counts.get('BEARISH_ALIGNED', 0)}")
    print(f"divergent={align_counts.get('DIVERGENT', 0)}")
    print(f"neutral={align_counts.get('NEUTRAL', 0)}")
    print(f"alignment_changes={alignment_changes}")
    print(f"collection_errors={collection_errors}")
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    print("reasons=" + ("|".join(reasons) if reasons else "OK"))
    print(f"output_path={path}")
    return 0 if status == "COMPLETED" else 1


def main(argv=None):
    args = build_parser().parse_args(argv)
    return run(args.symbol, cycles=args.cycles, interval=args.interval, output_dir=args.output_dir, execute=args.execute)


if __name__ == "__main__":
    sys.exit(main())
