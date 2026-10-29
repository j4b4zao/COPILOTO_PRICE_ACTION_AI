"""
tools/profit_rtd_rc17_parity_diagnostic.py

RC17-D2 - MARKET STRUCTURE MATHEMATICAL PARITY DIAGNOSTIC

Compara:

    MarketStructure RC17 ORIGINAL
                versus
    reprodução independente RC17-D1

usando exatamente o mesmo AnalysisContext e os mesmos candles.

REGRAS DE SEGURANÇA
-------------------
- Research only.
- Observational only.
- Não altera MarketStructure.
- Não altera PriceAction.
- Não altera gates.
- Não altera Strategy.
- Não altera Score.
- Não altera Risk.
- Não altera Decision.
- Não altera Alert.
- Não executa ordens.
- Não promove regra.
- Não modifica thresholds ou pesos.

RC17-D2
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from tools.profit_rtd_order_flow_combined_session import _build_sources
from tools.profit_rtd_rc17_swing_diagnostic import analyze_closed_candles


VERSION = "RC17-D2-MATHEMATICAL-PARITY"

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


def _bool(value: Any) -> bool:
    return bool(value)


def _original_structure(context: Any) -> dict[str, Any]:

    structure = getattr(context, "structure", None)

    if structure is None:
        return {
            "available": False,
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
        "available": True,
        "valid": _bool(getattr(structure, "valid", False)),
        "hh": _bool(getattr(structure, "hh", False)),
        "hl": _bool(getattr(structure, "hl", False)),
        "lh": _bool(getattr(structure, "lh", False)),
        "ll": _bool(getattr(structure, "ll", False)),
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
        "bos_up": _bool(
            getattr(structure, "bos_up", False)
        ),
        "bos_down": _bool(
            getattr(structure, "bos_down", False)
        ),
        "choch": _bool(
            getattr(structure, "choch", False)
        ),
    }


def _independent_structure(
    candles: list[Any],
) -> dict[str, Any]:

    if len(candles) < 6:

        return {
            "available": False,
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
            "available": False,
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
        "available": True,
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


def _same_price(
    first: Any,
    second: Any,
) -> bool:

    if first is None and second is None:
        return True

    if first is None or second is None:
        return False

    try:
        return abs(
            float(first) - float(second)
        ) < 1e-9
    except (TypeError, ValueError):
        return first == second


def _fmt_price(value: Any) -> str:

    if value is None:
        return "NONE"

    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _compare(
    original: dict[str, Any],
    independent: dict[str, Any],
) -> dict[str, Any]:

    fields = {}

    fields["HH"] = (
        original["hh"]
        == independent["hh"]
    )

    fields["HL"] = (
        original["hl"]
        == independent["hl"]
    )

    fields["LH"] = (
        original["lh"]
        == independent["lh"]
    )

    fields["LL"] = (
        original["ll"]
        == independent["ll"]
    )

    fields["TREND"] = (
        original["trend"]
        == independent["trend"]
    )

    fields["SWING_HIGH"] = _same_price(
        original["swing_high"],
        independent["swing_high"],
    )

    fields["SWING_LOW"] = _same_price(
        original["swing_low"],
        independent["swing_low"],
    )

    # A paridade estrutural principal usa exatamente
    # os campos produzidos pela matemática de swings.
    structural_match = all(
        fields.values()
    )

    return {
        "fields": fields,
        "structural_match": structural_match,
    }


def _print_header(symbol: str) -> None:

    print()
    print("=" * 78)
    print("RC17-D2 - MATHEMATICAL PARITY DIAGNOSTIC")
    print("=" * 78)

    print(f"version={VERSION}")
    print(f"symbol={symbol}")

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
    print("RC17-D2 PARITY SNAPSHOT")
    print("=" * 78)

    print(f"cycle={cycle}")
    print(f"candles_total={len(candles)}")
    print(
        f"candles_closed="
        f"{max(len(candles) - 1, 0)}"
    )

    print()
    print("-" * 78)
    print("RC17 ORIGINAL")
    print("-" * 78)

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
    print("-" * 78)
    print("D1 INDEPENDENTE")
    print("-" * 78)

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
    print("-" * 78)
    print("PARIDADE")
    print("-" * 78)

    for field, matched in (
        comparison["fields"].items()
    ):

        print(
            f"{field}_MATCH={matched}"
        )

    print(
        "STRUCTURAL_MATCH="
        f"{comparison['structural_match']}"
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

                candle_count = len(
                    candles
                )

                # Não há estrutura RC17 analisável
                # antes de seis candles totais.
                if candle_count >= 6:

                    # Um snapshot por mudança na
                    # quantidade de candles.
                    if (
                        candle_count
                        != last_reported_candle_count
                    ):

                        original = (
                            _original_structure(
                                context
                            )
                        )

                        independent = (
                            _independent_structure(
                                candles
                            )
                        )

                        comparison = _compare(
                            original,
                            independent,
                        )

                        parity_snapshots += 1

                        if comparison[
                            "structural_match"
                        ]:

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
                    f"[RC17-D2] "
                    f"cycle={cycle}/{cycles} "
                    f"analyzable={analyzable} "
                    f"skipped={skipped} "
                    f"errors={errors} "
                    f"parity_snapshots="
                    f"{parity_snapshots} "
                    f"matches="
                    f"{matched_snapshots} "
                    f"mismatches="
                    f"{mismatched_snapshots}"
                )

        except Exception as exc:

            errors += 1

            print(
                f"[RC17-D2] "
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
        matched_snapshots
        / parity_snapshots
        if parity_snapshots
        else 0.0
    )

    print()
    print("=" * 78)
    print("RC17-D2 FINAL")
    print("=" * 78)

    print(
        f"cycles={int(cycles)}"
    )

    print(
        f"analyzable_samples="
        f"{analyzable}"
    )

    print(
        f"skipped_cycles="
        f"{skipped}"
    )

    print(
        f"errors={errors}"
    )

    print(
        f"parity_snapshots="
        f"{parity_snapshots}"
    )

    print(
        f"matched_snapshots="
        f"{matched_snapshots}"
    )

    print(
        f"mismatched_snapshots="
        f"{mismatched_snapshots}"
    )

    print(
        f"parity_rate="
        f"{parity_rate:.6f}"
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
            "FULL_PARITY_OBSERVED"
        )

    elif parity_snapshots > 0:

        print(
            "parity_status="
            "MISMATCH_OBSERVED"
        )

    else:

        print(
            "parity_status="
            "INSUFFICIENT_PARITY_SNAPSHOTS"
        )

    print()
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
            "RC17-D2: paridade matematica "
            "entre MarketStructure RC17 "
            "e reproducao independente D1."
        )
    )

    parser.add_argument(
        "symbol",
        help=(
            "Ativo observado, "
            "por exemplo WINV26."
        ),
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