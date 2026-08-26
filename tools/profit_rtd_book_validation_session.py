"""Sessão contínua observacional do Livro de Ofertas RTD do Profit (RC27)."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from config.settings import PROFIT_RTD_ORDER_BOOK_PATH
from connectors.excel_connector import ExcelConnector
from market_data.book_depth_level2_provider import NormalizedLevel2BookDepthProvider
from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_session_recorder import BookDepthSessionRecorder
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics
from market_data.excel_range_gateway import ExcelRangeGateway
from market_data.profit_rtd_workbook_reader import ProfitRTDBookDepthReader


def run_session(symbol: str, *, cycles: int = 120, interval: float = 0.25, output_dir=None, sleeper=time.sleep):
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        raise ValueError("symbol é obrigatório.")
    if isinstance(cycles, bool) or int(cycles) < 1:
        raise ValueError("cycles deve ser inteiro >= 1.")
    if isinstance(interval, bool) or float(interval) < 0:
        raise ValueError("interval deve ser >= 0.")

    excel = ExcelConnector()
    if not excel.conectar(PROFIT_RTD_ORDER_BOOK_PATH):
        return {
            "status": "ERROR",
            "symbol": symbol,
            "requested_cycles": int(cycles),
            "completed_cycles": 0,
            "observational_only": True,
            "score_influence_allowed": False,
            "decision_influence_allowed": False,
            "order_execution_allowed": False,
            "reasons": ["EXCEL_CONNECTION_ERROR"],
        }

    gateway = ExcelRangeGateway(excel)
    reader = ProfitRTDBookDepthReader(gateway)
    provider = NormalizedLevel2BookDepthProvider(reader, source="PROFIT_RTD", max_levels=50)
    diagnostics = BookDepthSourceDiagnostics()
    quality_validator = BookDepthQualityValidator()
    recorder = BookDepthSessionRecorder(max_samples=max(int(cycles), 1))

    completed = 0
    collection_errors = 0
    last_best_bid = None
    last_best_ask = None
    quote_changes = 0

    for cycle in range(1, int(cycles) + 1):
        snapshot = provider.snapshot(symbol)
        source = diagnostics.observe(snapshot)
        quality = quality_validator.evaluate(snapshot, source)
        recorder.record(source, quality)
        completed = cycle

        if not bool(getattr(snapshot, "available", False)):
            collection_errors += 1
        else:
            best_bid = float(getattr(snapshot, "best_bid", 0.0) or 0.0)
            best_ask = float(getattr(snapshot, "best_ask", 0.0) or 0.0)
            if last_best_bid is not None and (best_bid != last_best_bid or best_ask != last_best_ask):
                quote_changes += 1
            last_best_bid = best_bid
            last_best_ask = best_ask

        print(
            "[BOOK RTD VALIDATION] "
            f"cycle={cycle}/{cycles} source={source.status} quality={quality.status} "
            f"fresh={source.fresh_snapshots} duplicates={source.duplicate_snapshots} "
            f"availability={source.availability_rate:.0%} bids={source.bid_levels} asks={source.ask_levels} "
            f"spread={source.spread:.2f} imbalance={source.imbalance:.4f} anomalies={quality.anomaly_count}"
        )

        if cycle < int(cycles) and interval > 0:
            sleeper(float(interval))

    source = diagnostics.report
    summary = recorder.summary()
    reasons = []
    if completed < int(cycles):
        reasons.append("INCOMPLETE_SESSION")
    if source.availability_rate < 0.80:
        reasons.append("LOW_AVAILABILITY")
    if source.fresh_snapshots < 3:
        reasons.append("INSUFFICIENT_FRESH_SNAPSHOTS")
    if source.symbol_changes > 0:
        reasons.append("SYMBOL_CHANGE")
    if summary.get("total_anomalies", 0) > 0:
        reasons.append("QUALITY_ANOMALIES")
    if quote_changes <= 0:
        reasons.append("NO_BEST_QUOTE_CHANGES")

    status = "COMPLETED" if not reasons else "COMPLETED_WITH_WARNINGS"
    result = {
        "status": status,
        "symbol": symbol,
        "requested_cycles": int(cycles),
        "completed_cycles": completed,
        "fresh_snapshots": source.fresh_snapshots,
        "duplicate_snapshots": source.duplicate_snapshots,
        "availability_rate": source.availability_rate,
        "symbol_changes": source.symbol_changes,
        "quote_changes": quote_changes,
        "last_best_bid": last_best_bid,
        "last_best_ask": last_best_ask,
        "last_spread": source.spread,
        "collection_errors": collection_errors,
        "summary": summary,
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
        "reasons": reasons,
    }

    if output_dir is not None:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        jsonl_path = target_dir / f"profit_rtd_book_samples_{symbol}_{stamp}.jsonl"
        summary_path = target_dir / f"profit_rtd_book_validation_{symbol}_{stamp}.json"
        recorder.save_jsonl(jsonl_path)
        summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["samples_path"] = str(jsonl_path)
        result["summary_path"] = str(summary_path)

    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sessão contínua observacional do Livro de Ofertas RTD.")
    parser.add_argument("symbol")
    parser.add_argument("--cycles", type=int, default=120)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--output-dir", default=r"C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_book_validation")
    args = parser.parse_args(argv)

    result = run_session(args.symbol, cycles=args.cycles, interval=args.interval, output_dir=args.output_dir)
    print(f"PROFIT_RTD_BOOK_SESSION={result['status']}")
    for key in (
        "symbol", "requested_cycles", "completed_cycles", "fresh_snapshots", "duplicate_snapshots",
        "availability_rate", "symbol_changes", "quote_changes", "last_best_bid", "last_best_ask",
        "last_spread", "collection_errors", "observational_only", "score_influence_allowed",
        "decision_influence_allowed", "order_execution_allowed",
    ):
        print(f"{key}={result.get(key)}")
    print(f"reasons={'|'.join(result['reasons']) if result['reasons'] else 'OK'}")
    if result.get("summary_path"):
        print(f"summary_path={result['summary_path']}")
    if result.get("samples_path"):
        print(f"samples_path={result['samples_path']}")
    return 0 if result["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
