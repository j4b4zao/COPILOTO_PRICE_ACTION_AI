"""
tools/profit_rtd_rc17_swing_diagnostic.py

RC17-D1 - SWING 2-2 OBSERVATIONAL DIAGNOSTIC

Objetivo:
    Diagnosticar, de forma independente e observacional, a geometria
    Swing 2-2 utilizada pelo MarketStructure RC17.

IMPORTANTE:
    - NÃO altera MarketStructure.
    - NÃO altera PriceAction.
    - NÃO altera gates.
    - NÃO executa Strategy / Score / Risk / Decision / Alert.
    - NÃO executa ordens.
    - NÃO produz sinal operacional.
    - NÃO promove nenhuma regra.
    - ENABLE_ORDER_FLOW_SCORE permanece intocado.

O módulo utiliza o mesmo Collector empregado pela captura RTD para obter
o histórico de candles, mas reproduz localmente apenas a matemática
Swing 2-left / 2-right do RC17.

RC17-D1
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from tools.profit_rtd_order_flow_combined_session import _build_sources


VERSION = "RC17-D1-SWING-2-2-OBSERVATIONAL"

RESEARCH_ONLY = True
OBSERVATIONAL_ONLY = True
PREDICTIVE_CLAIM_ALLOWED = False

SCORE_INFLUENCE_ALLOWED = False
RISK_INFLUENCE_ALLOWED = False
DECISION_INFLUENCE_ALLOWED = False
ALERT_INFLUENCE_ALLOWED = False
ORDER_EXECUTION_ALLOWED = False
PROMOTION_ALLOWED = False


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


def _price(value: Any) -> float:
    return float(value)


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _candidate_reason_high(
    current: Any,
    left_1: Any,
    left_2: Any,
    right_1: Any,
    right_2: Any,
) -> tuple[bool, list[str]]:

    comparisons = (
        ("L1", _price(current.high), _price(left_1.high)),
        ("L2", _price(current.high), _price(left_2.high)),
        ("R1", _price(current.high), _price(right_1.high)),
        ("R2", _price(current.high), _price(right_2.high)),
    )

    failures: list[str] = []

    for label, current_value, neighbor_value in comparisons:
        if not current_value > neighbor_value:
            failures.append(
                f"H_atual={current_value:.2f} "
                f"nao_supera_{label}={neighbor_value:.2f}"
            )

    return not failures, failures


def _candidate_reason_low(
    current: Any,
    left_1: Any,
    left_2: Any,
    right_1: Any,
    right_2: Any,
) -> tuple[bool, list[str]]:

    comparisons = (
        ("L1", _price(current.low), _price(left_1.low)),
        ("L2", _price(current.low), _price(left_2.low)),
        ("R1", _price(current.low), _price(right_1.low)),
        ("R2", _price(current.low), _price(right_2.low)),
    )

    failures: list[str] = []

    for label, current_value, neighbor_value in comparisons:
        if not current_value < neighbor_value:
            failures.append(
                f"L_atual={current_value:.2f} "
                f"nao_fica_abaixo_{label}={neighbor_value:.2f}"
            )

    return not failures, failures


def analyze_closed_candles(closed_candles: list[Any]) -> dict[str, Any]:

    swing_highs: list[float] = []
    swing_lows: list[float] = []

    swing_high_indexes: list[int] = []
    swing_low_indexes: list[int] = []

    candidates: list[dict[str, Any]] = []

    if len(closed_candles) >= 5:

        for i in range(2, len(closed_candles) - 2):

            current = closed_candles[i]

            left_1 = closed_candles[i - 1]
            left_2 = closed_candles[i - 2]

            right_1 = closed_candles[i + 1]
            right_2 = closed_candles[i + 2]

            high_ok, high_failures = _candidate_reason_high(
                current,
                left_1,
                left_2,
                right_1,
                right_2,
            )

            low_ok, low_failures = _candidate_reason_low(
                current,
                left_1,
                left_2,
                right_1,
                right_2,
            )

            candle_number = i + 1

            if high_ok:
                swing_highs.append(_price(current.high))
                swing_high_indexes.append(candle_number)

            if low_ok:
                swing_lows.append(_price(current.low))
                swing_low_indexes.append(candle_number)

            candidates.append(
                {
                    "candle_number": candle_number,
                    "current": current,
                    "left_1": left_1,
                    "left_2": left_2,
                    "right_1": right_1,
                    "right_2": right_2,
                    "swing_high": high_ok,
                    "swing_low": low_ok,
                    "high_failures": high_failures,
                    "low_failures": low_failures,
                }
            )

    hh = False
    hl = False
    lh = False
    ll = False

    if len(swing_highs) >= 2:

        previous_high = swing_highs[-2]
        current_high = swing_highs[-1]

        hh = current_high > previous_high
        lh = current_high < previous_high

    if len(swing_lows) >= 2:

        previous_low = swing_lows[-2]
        current_low = swing_lows[-1]

        hl = current_low > previous_low
        ll = current_low < previous_low

    if hh and hl:
        trend = "UP"
        trend_reason = "HH + HL confirmados."

    elif lh and ll:
        trend = "DOWN"
        trend_reason = "LH + LL confirmados."

    elif swing_highs or swing_lows:
        trend = "SIDEWAYS"
        trend_reason = (
            "Existe pelo menos um swing confirmado, "
            "mas nao existe HH+HL nem LH+LL."
        )

    else:
        trend = "UNKNOWN"
        trend_reason = "Nenhum swing confirmado."

    return {
        "candidates": candidates,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "swing_high_indexes": swing_high_indexes,
        "swing_low_indexes": swing_low_indexes,
        "hh": hh,
        "hl": hl,
        "lh": lh,
        "ll": ll,
        "trend": trend,
        "trend_reason": trend_reason,
    }


def print_header(symbol: str) -> None:

    print()
    print("=" * 78)
    print("RC17-D1 - SWING 2-2 OBSERVATIONAL DIAGNOSTIC")
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


def print_report(
    *,
    symbol: str,
    cycle: int,
    candles: list[Any],
    analysis: dict[str, Any],
) -> None:

    closed_candles = candles[:-1]

    print()
    print("=" * 78)
    print("RC17-D1 SNAPSHOT")
    print("=" * 78)

    print(f"symbol={symbol}")
    print(f"cycle={cycle}")
    print(f"candles_total={len(candles)}")
    print(f"candles_closed={len(closed_candles)}")
    print("current_candle_excluded=True")

    print()
    print("-" * 78)
    print("CANDLES FECHADOS")
    print("-" * 78)

    for index, candle in enumerate(closed_candles, start=1):

        print(
            f"C{index:02d} | "
            f"O={_fmt(candle.open)} "
            f"H={_fmt(candle.high)} "
            f"L={_fmt(candle.low)} "
            f"C={_fmt(candle.close)}"
        )

    print()
    print("-" * 78)
    print("CANDIDATOS SWING 2-2")
    print("-" * 78)

    if not analysis["candidates"]:
        print("Nenhum candle elegivel para avaliacao Swing 2-2.")

    for item in analysis["candidates"]:

        number = item["candle_number"]

        current = item["current"]
        left_1 = item["left_1"]
        left_2 = item["left_2"]
        right_1 = item["right_1"]
        right_2 = item["right_2"]

        print()
        print(f"C{number:02d} CANDIDATO")

        print(
            "  HIGH | "
            f"L2={_fmt(left_2.high)} "
            f"L1={_fmt(left_1.high)} "
            f"ATUAL={_fmt(current.high)} "
            f"R1={_fmt(right_1.high)} "
            f"R2={_fmt(right_2.high)}"
        )

        print(
            f"  SWING_HIGH={item['swing_high']}"
        )

        if item["swing_high"]:
            print("  HIGH_REASON=CONFIRMADO_2_LEFT_2_RIGHT")
        else:
            print(
                "  HIGH_REASON="
                + "; ".join(item["high_failures"])
            )

        print(
            "  LOW  | "
            f"L2={_fmt(left_2.low)} "
            f"L1={_fmt(left_1.low)} "
            f"ATUAL={_fmt(current.low)} "
            f"R1={_fmt(right_1.low)} "
            f"R2={_fmt(right_2.low)}"
        )

        print(
            f"  SWING_LOW={item['swing_low']}"
        )

        if item["swing_low"]:
            print("  LOW_REASON=CONFIRMADO_2_LEFT_2_RIGHT")
        else:
            print(
                "  LOW_REASON="
                + "; ".join(item["low_failures"])
            )

    print()
    print("-" * 78)
    print("SWINGS CONFIRMADOS")
    print("-" * 78)

    if analysis["swing_highs"]:

        for index, price in zip(
            analysis["swing_high_indexes"],
            analysis["swing_highs"],
        ):
            print(
                f"SWING_HIGH=C{index:02d} "
                f"price={price:.2f}"
            )

    else:
        print("SWING_HIGH=NONE")

    if analysis["swing_lows"]:

        for index, price in zip(
            analysis["swing_low_indexes"],
            analysis["swing_lows"],
        ):
            print(
                f"SWING_LOW=C{index:02d} "
                f"price={price:.2f}"
            )

    else:
        print("SWING_LOW=NONE")

    print()
    print("-" * 78)
    print("ESTRUTURA REPRODUZIDA")
    print("-" * 78)

    print(f"HH={analysis['hh']}")
    print(f"HL={analysis['hl']}")
    print(f"LH={analysis['lh']}")
    print(f"LL={analysis['ll']}")

    print(f"TREND={analysis['trend']}")
    print(f"TREND_REASON={analysis['trend_reason']}")

    print()
    print("RC17_D1=DESCRIPTIVE_ONLY")
    print("operational_interpretation_allowed=False")

    print("=" * 78)
    print()


def run(
    symbol: str,
    *,
    cycles: int,
    interval: float,
) -> int:

    symbol = str(symbol or "").strip().upper()

    if not symbol:
        raise ValueError("symbol e obrigatorio.")

    if int(cycles) < 1:
        raise ValueError("cycles deve ser >= 1.")

    if float(interval) < 0:
        raise ValueError("interval deve ser >= 0.")

    print_header(symbol)

    collector, _book_provider = _build_sources()

    last_candle_count = -1

    analyzable = 0
    skipped = 0
    errors = 0

    for cycle in range(1, int(cycles) + 1):

        try:
            context = collector.get_data()

            if context is None:

                skipped += 1

                if cycle % 50 == 0:
                    print(
                        f"[RC17-D1] "
                        f"cycle={cycle}/{cycles} "
                        f"analyzable={analyzable} "
                        f"skipped={skipped} "
                        f"errors={errors} "
                        f"status=SOURCE_UNCHANGED_OR_INVALID"
                    )

            else:

                analyzable += 1

                candles = _market_candles(context)

                candle_count = len(candles)

                if candle_count != last_candle_count:

                    print(
                        f"[RC17-D1] "
                        f"cycle={cycle}/{cycles} "
                        f"analyzable={analyzable} "
                        f"candles={candle_count} "
                        f"status=CANDLE_COUNT_CHANGED"
                    )

                    last_candle_count = candle_count

                # O RC17 original somente entra na análise estrutural
                # quando existem pelo menos 6 candles totais.
                if candle_count >= 6:

                    closed_candles = candles[:-1]

                    analysis = analyze_closed_candles(
                        closed_candles
                    )

                    # Imprime somente quando o número de candles muda,
                    # evitando milhares de relatórios idênticos.
                    if candle_count == last_candle_count:

                        # Para não repetir no mesmo candle, usamos uma
                        # marca separada armazenada no próprio run.
                        marker = getattr(
                            run,
                            "_last_reported_candle_count",
                            None,
                        )

                        if marker != candle_count:

                            print_report(
                                symbol=symbol,
                                cycle=cycle,
                                candles=candles,
                                analysis=analysis,
                            )

                            setattr(
                                run,
                                "_last_reported_candle_count",
                                candle_count,
                            )

        except Exception as exc:

            errors += 1

            print(
                f"[RC17-D1] "
                f"cycle={cycle}/{cycles} "
                f"error={type(exc).__name__}:{exc}"
            )

        if cycle < int(cycles) and float(interval) > 0:
            time.sleep(float(interval))

    print()
    print("=" * 78)
    print("RC17-D1 FINAL")
    print("=" * 78)

    print(f"cycles={int(cycles)}")
    print(f"analyzable_samples={analyzable}")
    print(f"skipped_cycles={skipped}")
    print(f"errors={errors}")

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

    return 0


def main(argv=None) -> int:

    parser = argparse.ArgumentParser(
        description=(
            "RC17-D1: diagnostico observacional independente "
            "da geometria Swing 2-2."
        )
    )

    parser.add_argument(
        "symbol",
        help="Ativo observado, por exemplo WINV26.",
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
    raise SystemExit(main())