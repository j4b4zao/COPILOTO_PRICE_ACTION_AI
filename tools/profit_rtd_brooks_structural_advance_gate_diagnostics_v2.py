"""
tools/profit_rtd_brooks_structural_advance_gate_diagnostics_v2.py

Diagnóstico research-only das portas de confirmação estrutural
do Brooks Protective / Trailing Stop.

Replica a política de reconstrução do Management Lifecycle:
- EXACT_CANDLE_LAST_REVISION;
- cada sessão permanece isolada;
- candle_evidence como fonte OHLC;
- sentinel sintético;
- candle atual fechado incluído na análise;
- nenhuma alteração no algoritmo oficial.

Não influencia Score/Risk/Decision/Alert/execução.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace


SWING_LEFT = 2
SWING_RIGHT = 2
MIN_HISTORY = 7

STAGE = "BROOKS_STRUCTURAL_ADVANCE_GATE_DIAGNOSTICS_V2"
DEDUPLICATION = "EXACT_CANDLE_LAST_REVISION"


def _load(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def _pa(sample):
    value = sample.get("price_action")
    return value if isinstance(value, dict) else {}


def _evidence(sample):
    value = sample.get("candle_evidence")
    return value if isinstance(value, dict) else {}


def _candle_id(sample):
    return str(
        _evidence(sample).get("candle_id") or ""
    )


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _deduplicate(samples):
    latest = {}
    order = []

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        cid = _candle_id(sample)

        if not cid:
            continue

        if cid not in latest:
            order.append(cid)

        latest[cid] = sample

    return [
        latest[cid]
        for cid in order
    ]


def _to_candle(sample):
    evidence = _evidence(sample)

    return SimpleNamespace(
        open=_float(evidence.get("open")),
        high=_float(evidence.get("high")),
        low=_float(evidence.get("low")),
        close=_float(evidence.get("close")),
        candle_id=_candle_id(sample),
    )


def _synthetic_sentinel(last_candle):
    return SimpleNamespace(
        open=last_candle.close,
        high=last_candle.close,
        low=last_candle.close,
        close=last_candle.close,
        candle_id=(
            f"{last_candle.candle_id}|SENTINEL"
        ),
    )


def _confirmed_pivots(candles):
    pivots = []

    left = SWING_LEFT
    right = SWING_RIGHT

    for i in range(
        left,
        len(candles) - right,
    ):
        candle = candles[i]

        high = float(candle.high)
        low = float(candle.low)

        left_slice = candles[i - left:i]
        right_slice = candles[
            i + 1:i + 1 + right
        ]

        if all(
            high > float(x.high)
            for x in left_slice + right_slice
        ):
            pivots.append(
                ("HIGH", i, high)
            )

        if all(
            low < float(x.low)
            for x in left_slice + right_slice
        ):
            pivots.append(
                ("LOW", i, low)
            )

    return pivots


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


def _eligible_entry(sample):
    pa = _pa(sample)

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

    geometry = bool(
        pa.get(
            "brooks_stop_target_stop_geometry_valid"
        )
    )

    if not triggered:
        return None

    if direction not in {"BUY", "SELL"}:
        return None

    if not geometry:
        return None

    if entry_price <= 0 or initial_stop <= 0:
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


def _gate_analysis(
    candles,
    direction,
):
    result = {
        "history_ready": False,
        "pivot_any": False,
        "reference_swing_present": False,
        "prior_opposite_pivot_present": False,
        "later_opposite_pivot_present": False,
        "both_sides_present": False,
        "breakout_confirmed": False,
    }

    # Replica o comportamento da engine:
    # o último elemento é descartado.
    closed = list(candles[:-1])

    if len(closed) < MIN_HISTORY:
        return result

    result["history_ready"] = True

    pivots = _confirmed_pivots(closed)

    if pivots:
        result["pivot_any"] = True

    if direction == "BUY":

        swing_lows = [
            (i, p)
            for kind, i, p in pivots
            if kind == "LOW"
        ]

        swing_highs = [
            (i, p)
            for kind, i, p in pivots
            if kind == "HIGH"
        ]

        if not swing_lows:
            return result

        latest_index, _ = swing_lows[-1]

        result[
            "reference_swing_present"
        ] = True

        prior_highs = [
            p
            for i, p in swing_highs
            if i < latest_index
        ]

        later_highs = [
            p
            for i, p in swing_highs
            if i > latest_index
        ]

        result[
            "prior_opposite_pivot_present"
        ] = bool(prior_highs)

        result[
            "later_opposite_pivot_present"
        ] = bool(later_highs)

        if prior_highs and later_highs:

            result[
                "both_sides_present"
            ] = True

            if (
                max(later_highs)
                > max(prior_highs)
            ):
                result[
                    "breakout_confirmed"
                ] = True

    elif direction == "SELL":

        swing_highs = [
            (i, p)
            for kind, i, p in pivots
            if kind == "HIGH"
        ]

        swing_lows = [
            (i, p)
            for kind, i, p in pivots
            if kind == "LOW"
        ]

        if not swing_highs:
            return result

        latest_index, _ = swing_highs[-1]

        result[
            "reference_swing_present"
        ] = True

        prior_lows = [
            p
            for i, p in swing_lows
            if i < latest_index
        ]

        later_lows = [
            p
            for i, p in swing_lows
            if i > latest_index
        ]

        result[
            "prior_opposite_pivot_present"
        ] = bool(prior_lows)

        result[
            "later_opposite_pivot_present"
        ] = bool(later_lows)

        if prior_lows and later_lows:

            result[
                "both_sides_present"
            ] = True

            if (
                min(later_lows)
                < min(prior_lows)
            ):
                result[
                    "breakout_confirmed"
                ] = True

    return result


def _update_counts(
    counts,
    direction_counts,
    direction,
    gates,
):
    counts["observations"] += 1
    direction_counts[direction] += 1

    for key, value in gates.items():
        if value:
            counts[key] += 1


def diagnose_session(payload):
    samples = payload.get("samples") or []

    exact_samples = _deduplicate(samples)

    exact_candles = [
        _to_candle(sample)
        for sample in exact_samples
    ]

    counts = Counter()
    directions = Counter()

    entry_episodes = 0

    for entry_index, sample in enumerate(
        exact_samples
    ):
        entry = _eligible_entry(sample)

        if entry is None:
            continue

        entry_episodes += 1

        direction = entry["direction"]

        # Mesmo contrato do Lifecycle:
        # primeira observação ocorre no candle seguinte.
        for observation_index in range(
            entry_index + 1,
            len(exact_samples),
        ):
            closed_history = exact_candles[
                :observation_index + 1
            ]

            current = exact_candles[
                observation_index
            ]

            engine_history = list(
                closed_history
            )

            engine_history.append(
                _synthetic_sentinel(current)
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

    return {
        "exact_candles": len(exact_samples),
        "eligible_entry_episodes": entry_episodes,
        "counts": dict(counts),
        "directions": dict(directions),
    }


def diagnose_many(paths):
    sessions = []

    total_exact = 0
    total_episodes = 0

    counts = Counter()
    directions = Counter()

    for path in paths:
        payload = _load(path)

        report = diagnose_session(payload)

        report["source"] = str(path)

        sessions.append(report)

        total_exact += report[
            "exact_candles"
        ]

        total_episodes += report[
            "eligible_entry_episodes"
        ]

        counts.update(
            report.get("counts") or {}
        )

        directions.update(
            report.get("directions") or {}
        )

    return {
        "status": "COMPLETED",
        "stage": STAGE,
        "deduplication": DEDUPLICATION,
        "accepted_session_count": len(sessions),
        "exact_candles": total_exact,
        "eligible_entry_episodes": total_episodes,
        "counts": dict(counts),
        "direction_observations": dict(directions),
        "sessions": sessions,
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


def main(argv=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "paths",
        nargs="+",
    )

    parser.add_argument(
        "--output",
    )

    args = parser.parse_args(argv)

    report = diagnose_many(
        args.paths
    )

    if args.output:
        Path(args.output).write_text(
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
        report["accepted_session_count"],
    )

    print(
        "exact_candles=",
        report["exact_candles"],
    )

    print(
        "eligible_entry_episodes=",
        report["eligible_entry_episodes"],
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
            report["direction_observations"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())