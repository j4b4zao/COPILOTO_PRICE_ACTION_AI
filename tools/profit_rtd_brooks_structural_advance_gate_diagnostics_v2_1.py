"""
tools/profit_rtd_brooks_structural_advance_gate_diagnostics_v2_1.py

Brooks Structural Advance Gate Diagnostics V2.1.

Diagnostico research-only das portas de confirmacao estrutural
do Brooks Protective / Trailing Stop.

Objetivos:
- trabalhar somente sobre sessoes Brooks ja persistidas;
- deduplicar por EXACT_CANDLE_LAST_REVISION;
- reconstruir o historico a partir de candle_evidence;
- manter cada sessao completamente isolada;
- reproduzir a politica de historico do Management Lifecycle;
- usar sentinel sintetico para que todos os candles fechados
  ate o candle de observacao sejam considerados;
- decompor a regra de structural advance em portas;
- separar os resultados BUY e SELL;
- registrar os casos que chegaram a possuir pivots dos dois lados;
- medir a distancia da condicao final de breakout/breakdown;
- nao alterar ProtectiveTrailingStopDynamics;
- nao alterar RC54.3.2;
- nao calcular performance;
- nao influenciar Score, Risk, Decision, Alert ou execucao.

Interpretacao de breakout_distance:

BUY:
    later_high - prior_high

    > 0  = condicao estrutural confirmada
    = 0  = igualdade
    < 0  = faltaram pontos para romper o prior high

SELL:
    prior_low - later_low

    > 0  = condicao estrutural confirmada
    = 0  = igualdade
    < 0  = faltaram pontos para romper o prior low
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace


STAGE = "BROOKS_STRUCTURAL_ADVANCE_GATE_DIAGNOSTICS_V2_1"
DEDUPLICATION = "EXACT_CANDLE_LAST_REVISION"

MIN_HISTORY = 7
SWING_LEFT = 2
SWING_RIGHT = 2


# ============================================================
# SAFETY
# ============================================================

def _safety():
    return {
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "performance_validated": False,
        "promotion_allowed": False,
        "hypothesis_freeze_allowed": False,
    }


# ============================================================
# BASIC HELPERS
# ============================================================

def _load(path):
    return json.loads(
        Path(path).read_text(
            encoding="utf-8",
        )
    )


def _price_action(sample):
    if not isinstance(sample, dict):
        return {}

    value = sample.get("price_action")

    return value if isinstance(value, dict) else {}


def _evidence(sample):
    if not isinstance(sample, dict):
        return {}

    value = sample.get("candle_evidence")

    return value if isinstance(value, dict) else {}


def _candle_id(sample):
    return str(
        _evidence(sample).get("candle_id")
        or ""
    )


def _float(value, default=0.0):
    try:
        return float(value)

    except (TypeError, ValueError):
        return float(default)


def _normalize_direction(value):
    direction = str(
        value or ""
    ).upper().strip()

    if direction == "UP":
        return "BUY"

    if direction == "DOWN":
        return "SELL"

    if direction in {"BUY", "SELL"}:
        return direction

    return "NONE"


# ============================================================
# EXACT CANDLE RECONSTRUCTION
# ============================================================

def _deduplicate(samples):
    """
    Replica EXACT_CANDLE_LAST_REVISION.

    Mantem a ordem da primeira aparicao do candle_id,
    mas conserva a ultima revisao persistida desse candle.
    """

    latest = {}
    order = []

    for sample in samples:

        if not isinstance(sample, dict):
            continue

        candle_id = _candle_id(sample)

        if not candle_id:
            continue

        if candle_id not in latest:
            order.append(candle_id)

        latest[candle_id] = sample

    return [
        latest[candle_id]
        for candle_id in order
    ]


def _to_candle(sample):
    evidence = _evidence(sample)

    return SimpleNamespace(
        open=_float(evidence.get("open")),
        high=_float(evidence.get("high")),
        low=_float(evidence.get("low")),
        close=_float(evidence.get("close")),
        candle_id=str(
            evidence.get("candle_id")
            or ""
        ),
    )


def _synthetic_sentinel(last_candle):
    """
    Replica a politica usada pelo Management Lifecycle.

    ProtectiveTrailingStopDynamics ignora candles[-1].
    O sentinel garante que todos os candles fechados ate
    o candle de observacao sejam vistos pela engine/logica.
    """

    return SimpleNamespace(
        open=last_candle.close,
        high=last_candle.close,
        low=last_candle.close,
        close=last_candle.close,
        candle_id=(
            f"{last_candle.candle_id}|SENTINEL"
        ),
    )


# ============================================================
# PIVOT RECONSTRUCTION
# ============================================================

def _confirmed_pivots(candles):
    """
    Replica a politica 2-left / 2-right da engine oficial.

    HIGH:
        high atual estritamente maior que os highs
        dos 2 candles anteriores e 2 posteriores.

    LOW:
        low atual estritamente menor que os lows
        dos 2 candles anteriores e 2 posteriores.
    """

    pivots = []

    left = SWING_LEFT
    right = SWING_RIGHT

    for index in range(
        left,
        len(candles) - right,
    ):

        candle = candles[index]

        high = float(candle.high)
        low = float(candle.low)

        left_slice = candles[
            index - left:index
        ]

        right_slice = candles[
            index + 1:index + 1 + right
        ]

        high_confirmed = all(
            high > float(other.high)
            for other
            in left_slice + right_slice
        )

        low_confirmed = all(
            low < float(other.low)
            for other
            in left_slice + right_slice
        )

        if high_confirmed:
            pivots.append(
                (
                    "HIGH",
                    index,
                    high,
                )
            )

        if low_confirmed:
            pivots.append(
                (
                    "LOW",
                    index,
                    low,
                )
            )

    return pivots


# ============================================================
# ENTRY CONTRACT
# ============================================================

def _eligible_entry(sample):
    """
    Replica o filtro de entrada elegivel utilizado
    pelo Management Lifecycle.
    """

    pa = _price_action(sample)

    triggered = bool(
        pa.get(
            "brooks_stop_target_entry_triggered",
            pa.get(
                "brooks_entry_triggered",
                False,
            ),
        )
    )

    direction = _normalize_direction(
        pa.get(
            "brooks_stop_target_direction",
            pa.get(
                "brooks_signal_direction"
            ),
        )
    )

    entry_price = _float(
        pa.get(
            "brooks_stop_target_entry_price"
        )
    )

    initial_stop = _float(
        pa.get(
            "brooks_stop_target_initial_stop"
        )
    )

    stop_geometry_valid = bool(
        pa.get(
            "brooks_stop_target_stop_geometry_valid"
        )
    )

    if not triggered:
        return None

    if direction not in {
        "BUY",
        "SELL",
    }:
        return None

    if not stop_geometry_valid:
        return None

    if (
        entry_price <= 0
        or initial_stop <= 0
    ):
        return None

    if (
        direction == "BUY"
        and initial_stop >= entry_price
    ):
        return None

    if (
        direction == "SELL"
        and initial_stop <= entry_price
    ):
        return None

    return {
        "direction": direction,
        "entry_price": entry_price,
        "initial_stop": initial_stop,
    }


# ============================================================
# STRUCTURAL GATE ANALYSIS
# ============================================================

def _gate_analysis(
    candles,
    direction,
):
    """
    Decompoe a condicao estrutural da engine oficial.

    O ultimo candle recebido e descartado para reproduzir
    ProtectiveTrailingStopDynamics.

    Como o caller adiciona sentinel, closed passa a conter
    todos os candles fechados ate a observacao.
    """

    result = {
        "history_ready": False,
        "pivot_any": False,

        "reference_swing_present": False,

        "prior_opposite_pivot_present": False,
        "later_opposite_pivot_present": False,

        "both_sides_present": False,
        "breakout_confirmed": False,

        "reference_swing_index": None,
        "reference_swing_price": None,

        "prior_opposite_price": None,
        "later_opposite_price": None,

        "breakout_distance": None,
    }

    # Replica candles[:-1] da engine.
    closed = list(candles[:-1])

    if len(closed) < MIN_HISTORY:
        return result

    result["history_ready"] = True

    pivots = _confirmed_pivots(
        closed
    )

    if pivots:
        result["pivot_any"] = True

    # ========================================================
    # BUY
    # ========================================================

    if direction == "BUY":

        swing_lows = [
            (index, price)
            for kind, index, price
            in pivots
            if kind == "LOW"
        ]

        swing_highs = [
            (index, price)
            for kind, index, price
            in pivots
            if kind == "HIGH"
        ]

        if not swing_lows:
            return result

        latest_index, latest_price = (
            swing_lows[-1]
        )

        result[
            "reference_swing_present"
        ] = True

        result[
            "reference_swing_index"
        ] = latest_index

        result[
            "reference_swing_price"
        ] = latest_price

        prior_highs = [
            price
            for index, price
            in swing_highs
            if index < latest_index
        ]

        later_highs = [
            price
            for index, price
            in swing_highs
            if index > latest_index
        ]

        result[
            "prior_opposite_pivot_present"
        ] = bool(prior_highs)

        result[
            "later_opposite_pivot_present"
        ] = bool(later_highs)

        if not (
            prior_highs
            and later_highs
        ):
            return result

        result[
            "both_sides_present"
        ] = True

        prior_price = max(
            prior_highs
        )

        later_price = max(
            later_highs
        )

        result[
            "prior_opposite_price"
        ] = prior_price

        result[
            "later_opposite_price"
        ] = later_price

        # Positivo = breakout confirmado.
        # Zero = igualdade.
        # Negativo = distancia ainda faltante.
        distance = (
            later_price
            - prior_price
        )

        result[
            "breakout_distance"
        ] = distance

        if later_price > prior_price:
            result[
                "breakout_confirmed"
            ] = True

        return result

    # ========================================================
    # SELL
    # ========================================================

    if direction == "SELL":

        swing_highs = [
            (index, price)
            for kind, index, price
            in pivots
            if kind == "HIGH"
        ]

        swing_lows = [
            (index, price)
            for kind, index, price
            in pivots
            if kind == "LOW"
        ]

        if not swing_highs:
            return result

        latest_index, latest_price = (
            swing_highs[-1]
        )

        result[
            "reference_swing_present"
        ] = True

        result[
            "reference_swing_index"
        ] = latest_index

        result[
            "reference_swing_price"
        ] = latest_price

        prior_lows = [
            price
            for index, price
            in swing_lows
            if index < latest_index
        ]

        later_lows = [
            price
            for index, price
            in swing_lows
            if index > latest_index
        ]

        result[
            "prior_opposite_pivot_present"
        ] = bool(prior_lows)

        result[
            "later_opposite_pivot_present"
        ] = bool(later_lows)

        if not (
            prior_lows
            and later_lows
        ):
            return result

        result[
            "both_sides_present"
        ] = True

        prior_price = min(
            prior_lows
        )

        later_price = min(
            later_lows
        )

        result[
            "prior_opposite_price"
        ] = prior_price

        result[
            "later_opposite_price"
        ] = later_price

        # Positivo = breakdown confirmado.
        # Zero = igualdade.
        # Negativo = distancia ainda faltante.
        distance = (
            prior_price
            - later_price
        )

        result[
            "breakout_distance"
        ] = distance

        if later_price < prior_price:
            result[
                "breakout_confirmed"
            ] = True

        return result

    return result


# ============================================================
# COUNTERS
# ============================================================

def _update_counts(
    counts,
    direction_counts,
    direction,
    gates,
):
    counts[
        "observations"
    ] += 1

    direction_counts[
        direction
    ] += 1

    prefix = direction.lower()

    boolean_gates = (
        "history_ready",
        "pivot_any",
        "reference_swing_present",
        "prior_opposite_pivot_present",
        "later_opposite_pivot_present",
        "both_sides_present",
        "breakout_confirmed",
    )

    for key in boolean_gates:

        if gates.get(key):

            counts[key] += 1

            counts[
                f"{prefix}_{key}"
            ] += 1


# ============================================================
# SESSION DIAGNOSTIC
# ============================================================

def diagnose_session(payload):
    if not isinstance(payload, dict):
        raise TypeError(
            "payload must be dict"
        )

    raw_samples = (
        payload.get("samples")
        or []
    )

    exact_samples = _deduplicate(
        raw_samples
    )

    exact_candles = [
        _to_candle(sample)
        for sample
        in exact_samples
    ]

    counts = Counter()
    directions = Counter()

    entry_episodes = 0

    both_sides_cases = []

    for entry_index, sample in enumerate(
        exact_samples
    ):

        entry = _eligible_entry(
            sample
        )

        if entry is None:
            continue

        entry_episodes += 1

        direction = entry[
            "direction"
        ]

        # Mesmo contrato do Lifecycle:
        # o candle de entrada nao movimenta stop.
        # A primeira observacao e o candle seguinte.
        for observation_index in range(
            entry_index + 1,
            len(exact_samples),
        ):

            # Todos os candles fechados ate e incluindo
            # o candle de observacao.
            closed_history = exact_candles[
                :observation_index + 1
            ]

            current = exact_candles[
                observation_index
            ]

            # Sentinel para reproduzir exatamente
            # o comportamento usado no Lifecycle.
            engine_history = list(
                closed_history
            )

            engine_history.append(
                _synthetic_sentinel(
                    current
                )
            )

            gates = _gate_analysis(
                engine_history,
                direction,
            )

            _update_counts(
                counts,
                directions,
                direction,
                gates,
            )

            if gates.get(
                "both_sides_present"
            ):

                both_sides_cases.append(
                    {
                        "direction": direction,

                        "entry_candle_id":
                            _candle_id(
                                exact_samples[
                                    entry_index
                                ]
                            ),

                        "observation_candle_id":
                            _candle_id(
                                exact_samples[
                                    observation_index
                                ]
                            ),

                        "observation_exact_index":
                            observation_index,

                        "reference_swing_index":
                            gates.get(
                                "reference_swing_index"
                            ),

                        "reference_swing_price":
                            gates.get(
                                "reference_swing_price"
                            ),

                        "prior_opposite_price":
                            gates.get(
                                "prior_opposite_price"
                            ),

                        "later_opposite_price":
                            gates.get(
                                "later_opposite_price"
                            ),

                        "breakout_distance":
                            gates.get(
                                "breakout_distance"
                            ),

                        "breakout_confirmed":
                            bool(
                                gates.get(
                                    "breakout_confirmed"
                                )
                            ),
                    }
                )

    return {
        "raw_samples": len(
            raw_samples
        ),

        "exact_candles": len(
            exact_samples
        ),

        "eligible_entry_episodes":
            entry_episodes,

        "counts": dict(
            sorted(
                counts.items()
            )
        ),

        "direction_observations":
            dict(
                sorted(
                    directions.items()
                )
            ),

        "both_sides_cases":
            both_sides_cases,
    }


# ============================================================
# MULTI-SESSION DIAGNOSTIC
# ============================================================

def diagnose_many(paths):
    sessions = []

    total_raw = 0
    total_exact = 0
    total_episodes = 0

    counts = Counter()
    directions = Counter()

    all_both_sides_cases = []

    for session_index, path in enumerate(
        paths
    ):

        payload = _load(
            path
        )

        report = diagnose_session(
            payload
        )

        report[
            "session_index"
        ] = session_index

        report[
            "source"
        ] = str(path)

        sessions.append(
            report
        )

        total_raw += int(
            report.get(
                "raw_samples",
                0,
            )
        )

        total_exact += int(
            report.get(
                "exact_candles",
                0,
            )
        )

        total_episodes += int(
            report.get(
                "eligible_entry_episodes",
                0,
            )
        )

        counts.update(
            report.get(
                "counts"
            )
            or {}
        )

        directions.update(
            report.get(
                "direction_observations"
            )
            or {}
        )

        for case in (
            report.get(
                "both_sides_cases"
            )
            or []
        ):

            all_both_sides_cases.append(
                {
                    "session_index":
                        session_index,

                    "source":
                        str(path),

                    **case,
                }
            )

    # ========================================================
    # DISTANCE SUMMARY
    # ========================================================

    buy_distances = [
        float(
            case["breakout_distance"]
        )
        for case
        in all_both_sides_cases
        if (
            case.get("direction")
            == "BUY"
            and case.get(
                "breakout_distance"
            )
            is not None
        )
    ]

    sell_distances = [
        float(
            case["breakout_distance"]
        )
        for case
        in all_both_sides_cases
        if (
            case.get("direction")
            == "SELL"
            and case.get(
                "breakout_distance"
            )
            is not None
        )
    ]

    all_distances = (
        buy_distances
        + sell_distances
    )

    def distance_summary(values):
        if not values:
            return {
                "count": 0,
                "positive_count": 0,
                "zero_count": 0,
                "negative_count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "closest_to_zero": None,
            }

        return {
            "count": len(values),

            "positive_count": sum(
                value > 0
                for value in values
            ),

            "zero_count": sum(
                value == 0
                for value in values
            ),

            "negative_count": sum(
                value < 0
                for value in values
            ),

            "min": min(values),

            "max": max(values),

            "mean": (
                sum(values)
                / len(values)
            ),

            "closest_to_zero": min(
                values,
                key=lambda value: abs(value),
            ),
        }

    return {
        "status": "COMPLETED",

        "stage": STAGE,

        "deduplication":
            DEDUPLICATION,

        "accepted_session_count":
            len(sessions),

        "raw_samples":
            total_raw,

        "exact_candles":
            total_exact,

        "eligible_entry_episodes":
            total_episodes,

        "counts":
            dict(
                sorted(
                    counts.items()
                )
            ),

        "direction_observations":
            dict(
                sorted(
                    directions.items()
                )
            ),

        "buy_breakout_distance_summary":
            distance_summary(
                buy_distances
            ),

        "sell_breakout_distance_summary":
            distance_summary(
                sell_distances
            ),

        "all_breakout_distance_summary":
            distance_summary(
                all_distances
            ),

        "both_sides_cases":
            all_both_sides_cases,

        "sessions":
            sessions,

        **_safety(),
    }


# ============================================================
# CLI
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Brooks Structural Advance "
            "Gate Diagnostics V2.1"
        )
    )

    parser.add_argument(
        "paths",
        nargs="+",
    )

    parser.add_argument(
        "--output",
    )

    args = parser.parse_args(
        argv
    )

    report = diagnose_many(
        args.paths
    )

    if args.output:

        output = Path(
            args.output
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print(
        "status=",
        report["status"],
    )

    print(
        "stage=",
        report["stage"],
    )

    print(
        "accepted_session_count=",
        report[
            "accepted_session_count"
        ],
    )

    print(
        "raw_samples=",
        report[
            "raw_samples"
        ],
    )

    print(
        "exact_candles=",
        report[
            "exact_candles"
        ],
    )

    print(
        "eligible_entry_episodes=",
        report[
            "eligible_entry_episodes"
        ],
    )

    print(
        "counts=",
        json.dumps(
            report["counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "direction_observations=",
        json.dumps(
            report[
                "direction_observations"
            ],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "buy_breakout_distance_summary=",
        json.dumps(
            report[
                "buy_breakout_distance_summary"
            ],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "sell_breakout_distance_summary=",
        json.dumps(
            report[
                "sell_breakout_distance_summary"
            ],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "all_breakout_distance_summary=",
        json.dumps(
            report[
                "all_breakout_distance_summary"
            ],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "both_sides_case_count=",
        len(
            report[
                "both_sides_cases"
            ]
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )