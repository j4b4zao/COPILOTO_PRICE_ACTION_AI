"""
tools/profit_rtd_rc17_isolated_parity_diagnostic.py

RC17-D3 - ISOLATED SAME-CYCLE PARITY DIAGNOSTIC

Objetivo
-------
Comparar, sobre o MESMO AnalysisContext e os MESMOS candles:

    1. MarketStructure RC17 original, executado isoladamente.
    2. Reprodução matemática independente RC17-D1.

Não executa AnalysisPipeline completo.
Não executa Strategy / Score / Risk / Decision / Alert.
Não altera código de produção.
Não executa ordens.

RC17-D3
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from analysis.market_structure import MarketStructure
from tools.profit_rtd_order_flow_combined_session import _build_sources
from tools.profit_rtd_rc17_swing_diagnostic import analyze_closed_candles


VERSION = "RC17-D3-ISOLATED-SAME-CYCLE-PARITY"

RESEARCH_ONLY = True
OBSERVATIONAL_ONLY = True
PREDICTIVE_CLAIM_ALLOWED = False

SCORE_INFLUENCE_ALLOWED = False
RISK_INFLUENCE_ALLOWED = False
DECISION_INFLUENCE_ALLOWED = False
ALERT_INFLUENCE_ALLOWED = False
ORDER_EXECUTION_ALLOWED = False
PROMOTION_ALLOWED = False


def _enum_value(value: Any) -> str:
    if value is None:
        return "UNKNOWN"

    raw = getattr(value, "value", value)
    text = str(raw).strip().upper()

    if text.startswith("TREND."):
        text = text.split(".", 1)[1]

    return text or "UNKNOWN"


def _market_candles(context: Any) -> list[Any]:
    market = getattr(context, "market", None)

    if market is None:
        return []

    candles_obj = getattr(market, "candles", None)

    if candles_obj is None:
        return []

    all_method = getattr(candles_obj, "all", None)

    if not callable(all_method):
        return []

    candles = all_method()

    if candles is None:
        return []

    return list(candles)


def _fmt_price(value: Any) -> str:
    if value is None:
        return "NONE"

    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _same_price(first: Any, second: Any) -> bool:
    if first is None and second is None:
        return True

    if first is None or second is None:
        return False

    try:
        return abs(float(first) - float(second)) < 1e-9
    except (TypeError, ValueError):
        return first == second


def _snapshot_original(context: Any) -> dict[str, Any]:
    structure = getattr(context, "structure", None)

    if structure is None:
        return {
            "valid": False,
            "hh": False,
            "hl": False,
            "lh": False,
            "ll": False,
            "trend": "UNKNOWN",
            "swing_high": None,
            "swing_low": None,
            "bos_up": False,
            "bos_down": False,
            "choch": False,
        }

    return {
        "valid": bool(
            getattr(structure, "valid", False)
        ),
        "hh": bool(
            getattr(structure, "hh", False)
        ),
        "hl": bool(
            getattr(structure, "hl", False)
        ),
        "lh": bool(
            getattr(structure, "lh", False)
        ),
        "ll": bool(
            getattr(structure, "ll", False)
        ),
        "trend": _enum_value(
            getattr(structure, "trend", None)
        ),
        "swing_high": getattr(
            structure,
            "swing_high",
            None,
        ),
        "swing_low": getattr(
            structure,
            "swing_low",
            None,
        ),
        "bos_up": bool(
            getattr(structure, "bos_up", False)
        ),
        "bos_down": bool(
            getattr(structure, "bos_down", False)
        ),
        "choch": bool(
            getattr(structure, "choch", False)
        ),
    }


def _independent(candles: list[Any]) -> dict[str, Any]:
    if len(candles) < 6:
        return {
            "valid": False,
            "hh": False,
            "hl": False,
            "lh": False,
            "ll": False,
            "trend": "UNKNOWN",
            "swing_high": None,
            "swing_low": None,
            "swing_high_count": 0,
            "swing_low_count": 0,
        }

    closed_candles = candles[:-1]

    if len(closed_candles) < 5:
        return {
            "valid": False,
            "hh": False,
            "hl": False,
            "lh": False,
            "ll": False,
            "trend": "UNKNOWN",
            "swing_high": None,
            "swing_low": None,
            "swing_high_count": 0,
            "swing_low_count": 0,
        }

    result = analyze_closed_candles(
        closed_candles
    )

    swing_highs = list(
        result.get("swing_highs", [])
    )

    swing_lows = list(
        result.get("swing_lows", [])
    )

    has_any_swing = bool(
        swing_highs or swing_lows
    )

    return {
        "valid": has_any_swing,
        "hh": bool(result["hh"]),
        "hl": bool(result["hl"]),
        "lh": bool(result["lh"]),
        "ll": bool(result["ll"]),
        "trend": str(
            result["trend"]
        ).strip().upper(),
        "swing_high": (
            swing_highs[-1]
            if swing_highs
            else None
        ),
        "swing_low": (
            swing_lows[-1]
            if swing_lows
            else None
        ),
        "swing_high_count": len(
            swing_highs
        ),
        "swing_low_count": len(
            swing_lows
        ),
    }


def _compare(
    original: dict[str, Any],
    independent: dict[str, Any],
) -> dict[str, Any]:

    fields = {
        "VALID": (
            original["valid"]
            == independent["valid"]
        ),
        "HH": (
            original["hh"]
            == independent["hh"]
        ),
        "HL": (
            original["hl"]
            == independent["hl"]
        ),
        "LH": (
            original["lh"]
            == independent["lh"]
        ),
        "LL": (
            original["ll"]
            == independent["ll"]
        ),
        "TREND": (
            original["trend"]
            == independent["trend"]
        ),
        "SWING_HIGH": _same_price(
            original["swing_high"],
            independent["swing_high"],
        ),
        "SWING_LOW": _same_price(
            original["swing_low"],
            independent["swing_low"],
        ),
    }

    return {
        "fields": fields,
        "match": all(fields.values()),
    }


def _print_header(symbol: str) -> None:
    print()
    print("=" * 78)
    print("RC17-D3 - ISOLATED SAME-CYCLE PARITY")
    print("=" * 78)

    print(f"version={VERSION}")
    print(f"symbol={symbol}")

    print("rc17_execution=ISOLATED_ONLY")
    print("analysis_pipeline_execution=False")
    print("strategy_execution=False")
    print("score_execution=False")
    print("risk_execution=False")
    print("decision_execution=False")
    print("alert_execution=False")

    print("research_only=True")
    print("observational_only=True")
    print("predictive_claim_allowed=False")
    print("score_influence_allowed=False")
    print("risk_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("alert_influence_allowed=False")
    print("order_execution_allowed=False")
    print("promotion_allowed=False")

    print("=" * 78)
    print()


def _print_snapshot(
    *,
    cycle: int,
    candles: list[Any],
    original: dict[str, Any],
    independent: dict[str, Any],
    comparison: dict[str, Any],
) -> None:

    print()
    print("=" * 78)
    print("RC17-D3 SNAPSHOT")
    print("=" * 78)

    print(f"cycle={cycle}")
    print(f"candles_total={len(candles)}")
    print(
        f"candles_closed="
        f"{max(len(candles) - 1, 0)}"
    )

    print()
    print("RC17_ORIGINAL_ISOLATED")

    print(
        f"valid={original['valid']}"
    )
    print(
        f"HH={original['hh']}"
    )
    print(
        f"HL={original['hl']}"
    )
    print(
        f"LH={original['lh']}"
    )
    print(
        f"LL={original['ll']}"
    )
    print(
        f"TREND={original['trend']}"
    )
    print(
        "SWING_HIGH="
        + _fmt_price(
            original["swing_high"]
        )
    )
    print(
        "SWING_LOW="
        + _fmt_price(
            original["swing_low"]
        )
    )

    print(
        f"BOS_UP={original['bos_up']}"
    )
    print(
        f"BOS_DOWN={original['bos_down']}"
    )
    print(
        f"CHOCH={original['choch']}"
    )

    print()
    print("D1_INDEPENDENT")

    print(
        f"valid={independent['valid']}"
    )
    print(
        f"HH={independent['hh']}"
    )
    print(
        f"HL={independent['hl']}"
    )
    print(
        f"LH={independent['lh']}"
    )
    print(
        f"LL={independent['ll']}"
    )
    print(
        f"TREND={independent['trend']}"
    )
    print(
        "SWING_HIGH="
        + _fmt_price(
            independent["swing_high"]
        )
    )
    print(
        "SWING_LOW="
        + _fmt_price(
            independent["swing_low"]
        )
    )
    print(
        "SWING_HIGH_COUNT="
        f"{independent['swing_high_count']}"
    )
    print(
        "SWING_LOW_COUNT="
        f"{independent['swing_low_count']}"
    )

    print()
    print("PARITY")

    for field, matched in (
        comparison["fields"].items()
    ):
        print(
            f"{field}_MATCH={matched}"
        )

    print(
        "STRUCTURAL_MATCH="
        f"{comparison['match']}"
    )

    print("=" * 78)
    print()


def run(
    symbol: str,
    *,
    cycles: int,
    interval: float,
) -> int:

    symbol = str(
        symbol or ""
    ).strip().upper()

    if not symbol:
        raise ValueError(
            "symbol e obrigatorio."
        )

    if int(cycles) < 1:
        raise ValueError(
            "cycles deve ser >= 1."
        )

    if float(interval) < 0:
        raise ValueError(
            "interval deve ser >= 0."
        )

    _print_header(symbol)

    collector, _book_provider = (
        _build_sources()
    )

    # Instância isolada.
    # Não pertence ao AnalysisPipeline.
    rc17 = MarketStructure()

    analyzable = 0
    skipped = 0
    errors = 0

    parity_snapshots = 0
    matched_snapshots = 0
    mismatched_snapshots = 0

    mismatch_cycles: list[int] = []

    last_reported_candle_count = None

    for cycle in range(
        1,
        int(cycles) + 1,
    ):

        try:
            context = collector.get_data()

            if context is None:
                skipped += 1

            else:
                analyzable += 1

                candles = _market_candles(
                    context
                )

                candle_count = len(candles)

                if candle_count >= 6:
                    if (
                        candle_count
                        != last_reported_candle_count
                    ):
                        # --------------------------------------
                        # MESMO CICLO / MESMO CONTEXT
                        #
                        # Executa SOMENTE MarketStructure RC17.
                        # --------------------------------------
                        rc17.executar(context)

                        original = (
                            _snapshot_original(
                                context
                            )
                        )

                        independent = (
                            _independent(
                                candles
                            )
                        )

                        comparison = _compare(
                            original,
                            independent,
                        )

                        parity_snapshots += 1

                        if comparison["match"]:
                            matched_snapshots += 1
                        else:
                            mismatched_snapshots += 1
                            mismatch_cycles.append(
                                cycle
                            )

                        _print_snapshot(
                            cycle=cycle,
                            candles=candles,
                            original=original,
                            independent=independent,
                            comparison=comparison,
                        )

                        last_reported_candle_count = (
                            candle_count
                        )

            if cycle % 100 == 0:
                print(
                    f"[RC17-D3] "
                    f"cycle={cycle}/{cycles} "
                    f"analyzable={analyzable} "
                    f"skipped={skipped} "
                    f"errors={errors} "
                    f"snapshots={parity_snapshots} "
                    f"matches={matched_snapshots} "
                    f"mismatches={mismatched_snapshots}"
                )

        except Exception as exc:
            errors += 1

            print(
                f"[RC17-D3] "
                f"cycle={cycle}/{cycles} "
                f"error="
                f"{type(exc).__name__}:{exc}"
            )

        if (
            cycle < int(cycles)
            and float(interval) > 0
        ):
            time.sleep(
                float(interval)
            )

    parity_rate = (
        matched_snapshots / parity_snapshots
        if parity_snapshots
        else 0.0
    )

    print()
    print("=" * 78)
    print("RC17-D3 FINAL")
    print("=" * 78)

    print(
        f"cycles={int(cycles)}"
    )
    print(
        f"analyzable_samples={analyzable}"
    )
    print(
        f"skipped_cycles={skipped}"
    )
    print(
        f"errors={errors}"
    )

    print(
        f"parity_snapshots={parity_snapshots}"
    )
    print(
        f"matched_snapshots={matched_snapshots}"
    )
    print(
        f"mismatched_snapshots={mismatched_snapshots}"
    )
    print(
        f"parity_rate={parity_rate:.6f}"
    )

    if mismatch_cycles:
        print(
            "mismatch_cycles="
            + ",".join(
                str(value)
                for value in mismatch_cycles
            )
        )
    else:
        print(
            "mismatch_cycles=NONE"
        )

    if (
        parity_snapshots > 0
        and mismatched_snapshots == 0
    ):
        print(
            "parity_status="
            "FULL_SAME_CYCLE_PARITY"
        )

    elif parity_snapshots > 0:
        print(
            "parity_status="
            "TRUE_MATH_MISMATCH_OBSERVED"
        )

    else:
        print(
            "parity_status="
            "INSUFFICIENT_PARITY_SNAPSHOTS"
        )

    print()
    print(
        "analysis_pipeline_execution=False"
    )
    print(
        "rc17_execution=ISOLATED_ONLY"
    )

    print("research_only=True")
    print("observational_only=True")
    print(
        "predictive_claim_allowed=False"
    )
    print(
        "score_influence_allowed=False"
    )
    print(
        "risk_influence_allowed=False"
    )
    print(
        "decision_influence_allowed=False"
    )
    print(
        "alert_influence_allowed=False"
    )
    print(
        "order_execution_allowed=False"
    )
    print(
        "promotion_allowed=False"
    )

    print("=" * 78)

    return 0


def main(argv=None) -> int:

    parser = argparse.ArgumentParser(
        description=(
            "RC17-D3: paridade same-cycle "
            "entre RC17 isolado e D1."
        )
    )

    parser.add_argument(
        "symbol",
        help="Ativo observado, ex. WINV26.",
    )

    parser.add_argument(
        "--cycles",
        type=int,
        default=1200,
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
    )

    args = parser.parse_args(argv)

    return run(
        args.symbol,
        cycles=args.cycles,
        interval=args.interval,
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )