"""Sessao observacional RC32/RC36: compara alinhamento oficial vs shadow em T&T + Book RTD."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from datetime import datetime

from config.settings import ENABLE_ORDER_FLOW_SCORE
from market_data.order_flow_shadow_calibration import OrderFlowShadowCalibration
from tools.profit_rtd_order_flow_combined_session import _build_sources
from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics
from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator

MAX_CYCLES = 3600
DIRECTION_LOGIC_VERSION = "RC35_SIGNED_DELTA"


def build_parser():
    p = argparse.ArgumentParser(description="Compara thresholds oficiais e shadow sem efeito operacional.")
    p.add_argument("symbol")
    p.add_argument("--cycles", required=True, type=int)
    p.add_argument("--interval", type=float, default=0.25)
    p.add_argument("--delta-threshold", type=float, default=0.35)
    p.add_argument("--book-threshold", type=float, default=0.062149)
    p.add_argument("--output-dir", default=r"C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_order_flow_shadow")
    p.add_argument("--execute", action="store_true")
    return p


def run(symbol, *, cycles, interval, delta_threshold, book_threshold, output_dir, execute=False, sleeper=time.sleep):
    if not execute:
        print("PROFIT_RTD_ORDER_FLOW_SHADOW=NOT_STARTED")
        print("reason=EXECUTE_FLAG_REQUIRED")
        return 2
    if ENABLE_ORDER_FLOW_SCORE:
        print("PROFIT_RTD_ORDER_FLOW_SHADOW=NOT_STARTED")
        print("reason=ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED")
        return 2
    if not (1 <= int(cycles) <= MAX_CYCLES) or float(interval) < 0:
        print("PROFIT_RTD_ORDER_FLOW_SHADOW=NOT_STARTED")
        print("reason=INVALID_CYCLES_OR_INTERVAL")
        return 2

    symbol = str(symbol or "").strip().upper()
    target = Path(output_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    try:
        collector, book_provider = _build_sources()
        shadow = OrderFlowShadowCalibration(
            delta_threshold=delta_threshold,
            book_threshold=book_threshold,
        )
    except Exception as exc:
        print("PROFIT_RTD_ORDER_FLOW_SHADOW=ERROR")
        print(f"reason=BOOTSTRAP_ERROR:{type(exc).__name__}:{exc}")
        return 1

    delta_validator = ProfitDeltaQualityValidator()
    book_diag = BookDepthSourceDiagnostics()
    book_validator = BookDepthQualityValidator()
    builder = OrderFlowObservationalContextBuilder()

    official_counts = {"BULLISH_ALIGNED": 0, "BEARISH_ALIGNED": 0, "DIVERGENT": 0, "NEUTRAL": 0}
    shadow_counts = {"BULLISH_ALIGNED": 0, "BEARISH_ALIGNED": 0, "DIVERGENT": 0, "NEUTRAL": 0}
    samples = []
    changed_count = 0
    collection_errors = 0

    for cycle in range(1, int(cycles) + 1):
        try:
            collector.get_data()
            book = book_provider.snapshot(symbol)
            source_report = book_diag.observe(book)
            book_report = book_validator.evaluate(book, source_report)
            delta_report = delta_validator.evaluate(collector.order_flow)
            context = builder.build(delta_report=delta_report, book_report=book_report, symbol=symbol)
            result = shadow.evaluate(context)
        except Exception as exc:
            collection_errors += 1
            print(f"[ORDER FLOW SHADOW] cycle={cycle}/{cycles} error={type(exc).__name__}:{exc}")
            if cycle < int(cycles) and float(interval) > 0:
                sleeper(float(interval))
            continue

        official_counts[result.official_alignment] = official_counts.get(result.official_alignment, 0) + 1
        shadow_counts[result.shadow_alignment] = shadow_counts.get(result.shadow_alignment, 0) + 1
        if result.changed:
            changed_count += 1

        samples.append({
            "cycle": cycle,
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "status": context.status,
            "official_alignment": result.official_alignment,
            "shadow_alignment": result.shadow_alignment,
            "changed": result.changed,
            "recent_delta": result.recent_delta,
            "dominance": result.dominance,
            "imbalance": result.imbalance,
            "delta_threshold": result.delta_threshold,
            "book_threshold": result.book_threshold,
            "direction_logic_version": DIRECTION_LOGIC_VERSION,
            "observational_only": True,
            "score_influence_allowed": False,
            "decision_influence_allowed": False,
            "order_execution_allowed": False,
        })
        print(
            f"[ORDER FLOW SHADOW] cycle={cycle}/{cycles} status={context.status} "
            f"official={result.official_alignment} shadow={result.shadow_alignment} changed={result.changed} "
            f"delta={result.recent_delta:.2f} dominance={result.dominance:.4f} imbalance={result.imbalance:.4f}"
        )
        if cycle < int(cycles) and float(interval) > 0:
            sleeper(float(interval))

    completed = len(samples)
    status = "COMPLETED" if completed == int(cycles) and collection_errors == 0 else "COMPLETED_WITH_WARNINGS"
    reasons = [] if status == "COMPLETED" else ["COLLECTION_ERRORS_OR_SKIPPED_CYCLES"]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target / f"profit_rtd_order_flow_shadow_{symbol}_{stamp}.json"
    payload = {
        "status": status,
        "symbol": symbol,
        "requested_cycles": int(cycles),
        "completed_cycles": completed,
        "delta_threshold": float(delta_threshold),
        "book_threshold": float(book_threshold),
        "direction_logic_version": DIRECTION_LOGIC_VERSION,
        "official_counts": official_counts,
        "shadow_counts": shadow_counts,
        "changed_count": changed_count,
        "collection_errors": collection_errors,
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
        "reasons": reasons,
        "samples": samples,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PROFIT_RTD_ORDER_FLOW_SHADOW={status}")
    print(f"symbol={symbol}")
    print(f"requested_cycles={cycles}")
    print(f"completed_cycles={completed}")
    print(f"delta_threshold={float(delta_threshold):.6f}")
    print(f"book_threshold={float(book_threshold):.6f}")
    print(f"direction_logic_version={DIRECTION_LOGIC_VERSION}")
    print(f"official_bullish={official_counts.get('BULLISH_ALIGNED', 0)}")
    print(f"official_bearish={official_counts.get('BEARISH_ALIGNED', 0)}")
    print(f"official_divergent={official_counts.get('DIVERGENT', 0)}")
    print(f"official_neutral={official_counts.get('NEUTRAL', 0)}")
    print(f"shadow_bullish={shadow_counts.get('BULLISH_ALIGNED', 0)}")
    print(f"shadow_bearish={shadow_counts.get('BEARISH_ALIGNED', 0)}")
    print(f"shadow_divergent={shadow_counts.get('DIVERGENT', 0)}")
    print(f"shadow_neutral={shadow_counts.get('NEUTRAL', 0)}")
    print(f"changed_count={changed_count}")
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
    return run(
        args.symbol,
        cycles=args.cycles,
        interval=args.interval,
        delta_threshold=args.delta_threshold,
        book_threshold=args.book_threshold,
        output_dir=args.output_dir,
        execute=args.execute,
    )


if __name__ == "__main__":
    sys.exit(main())
