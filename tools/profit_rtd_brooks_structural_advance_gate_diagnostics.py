"""
tools/profit_rtd_brooks_structural_advance_gate_diagnostics.py

Diagnóstico research-only das portas necessárias para a confirmação
estrutural do trailing stop Brooks.

Não altera o contrato RC54.3.2.
Não altera Score/Risk/Decision/Alert/execução.
Não modifica os arquivos de evidência.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SWING_LEFT = 2
SWING_RIGHT = 2


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pa(sample):
    value = sample.get("price_action")
    return value if isinstance(value, dict) else {}


def _candle_id(sample):
    evidence = sample.get("candle_evidence")
    if not isinstance(evidence, dict):
        return ""
    return str(evidence.get("candle_id") or "")


def _last_revision(samples):
    by_id = {}
    order = []

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        cid = _candle_id(sample)
        if not cid:
            continue

        if cid not in by_id:
            order.append(cid)

        by_id[cid] = sample

    return [by_id[cid] for cid in order]


def _extract_candles(sample):
    """
    Procura o histórico de candles persistido no sample.

    Aceita formatos conhecidos/possíveis sem modificar a origem.
    """

    candidates = (
        sample.get("candles"),
        sample.get("history"),
        sample.get("candle_history"),
        sample.get("market_history"),
    )

    market = sample.get("market")
    if isinstance(market, dict):
        candidates += (
            market.get("candles"),
            market.get("history"),
        )

    evidence = sample.get("candle_evidence")
    if isinstance(evidence, dict):
        candidates += (
            evidence.get("candles"),
            evidence.get("history"),
        )

    for value in candidates:
        if isinstance(value, list) and value:
            return value

    return []


def _high(candle):
    if isinstance(candle, dict):
        value = candle.get("high")
        if value is None:
            value = candle.get("max")
        return float(value)

    return float(candle.high)


def _low(candle):
    if isinstance(candle, dict):
        value = candle.get("low")
        if value is None:
            value = candle.get("min")
        return float(value)

    return float(candle.low)


def _confirmed_pivots(candles):
    pivots = []

    left = SWING_LEFT
    right = SWING_RIGHT

    for i in range(left, len(candles) - right):
        candle = candles[i]

        high = _high(candle)
        low = _low(candle)

        left_slice = candles[i - left:i]
        right_slice = candles[i + 1:i + 1 + right]

        if all(
            high > _high(x)
            for x in left_slice + right_slice
        ):
            pivots.append(("HIGH", i, high))

        if all(
            low < _low(x)
            for x in left_slice + right_slice
        ):
            pivots.append(("LOW", i, low))

    return pivots


def _diagnose_sample(sample):
    pa = _pa(sample)

    status = str(
        pa.get("brooks_management_capture_status") or ""
    )

    direction = str(
        pa.get("brooks_management_direction") or ""
    ).upper()

    result = {
        "eligible": status in {"CAPTURED", "REJECTED"},
        "direction": direction,
        "history_available": False,
        "reference_swing_present": False,
        "prior_opposite_pivot_present": False,
        "later_opposite_pivot_present": False,
        "breakout_confirmed": False,
        "structural_advance_confirmed": bool(
            pa.get(
                "brooks_management_structural_advance_confirmed"
            )
        ),
    }

    if not result["eligible"]:
        return result

    candles = _extract_candles(sample)

    if not candles:
        return result

    # Mesmo contrato do motor:
    # candle atual não participa.
    closed = list(candles[:-1])

    if len(closed) < 7:
        return result

    result["history_available"] = True

    pivots = _confirmed_pivots(closed)

    if direction == "BUY":
        lows = [
            (i, p)
            for kind, i, p in pivots
            if kind == "LOW"
        ]

        highs = [
            (i, p)
            for kind, i, p in pivots
            if kind == "HIGH"
        ]

        if not lows:
            return result

        latest_index, _ = lows[-1]
        result["reference_swing_present"] = True

        prior = [
            p for i, p in highs
            if i < latest_index
        ]

        later = [
            p for i, p in highs
            if i > latest_index
        ]

        result[
            "prior_opposite_pivot_present"
        ] = bool(prior)

        result[
            "later_opposite_pivot_present"
        ] = bool(later)

        if prior and later:
            result["breakout_confirmed"] = (
                max(later) > max(prior)
            )

    elif direction == "SELL":
        highs = [
            (i, p)
            for kind, i, p in pivots
            if kind == "HIGH"
        ]

        lows = [
            (i, p)
            for kind, i, p in pivots
            if kind == "LOW"
        ]

        if not highs:
            return result

        latest_index, _ = highs[-1]
        result["reference_swing_present"] = True

        prior = [
            p for i, p in lows
            if i < latest_index
        ]

        later = [
            p for i, p in lows
            if i > latest_index
        ]

        result[
            "prior_opposite_pivot_present"
        ] = bool(prior)

        result[
            "later_opposite_pivot_present"
        ] = bool(later)

        if prior and later:
            result["breakout_confirmed"] = (
                min(later) < min(prior)
            )

    return result


def _analyze(samples):
    counts = Counter()
    directions = Counter()

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        result = _diagnose_sample(sample)

        if not result["eligible"]:
            continue

        counts["eligible"] += 1
        directions[result["direction"]] += 1

        if result["history_available"]:
            counts["history_available"] += 1

        if result["reference_swing_present"]:
            counts["reference_swing_present"] += 1

        if result["prior_opposite_pivot_present"]:
            counts["prior_opposite_pivot_present"] += 1

        if result["later_opposite_pivot_present"]:
            counts["later_opposite_pivot_present"] += 1

        if (
            result["prior_opposite_pivot_present"]
            and result["later_opposite_pivot_present"]
        ):
            counts["both_sides_present"] += 1

        if result["breakout_confirmed"]:
            counts["breakout_confirmed"] += 1

        if result["structural_advance_confirmed"]:
            counts["engine_structural_advance_true"] += 1

    return {
        "counts": dict(counts),
        "directions": dict(directions),
    }


def diagnose_file(path):
    payload = _load(path)

    raw = [
        x
        for x in (payload.get("samples") or [])
        if isinstance(x, dict)
    ]

    exact = _last_revision(raw)

    return {
        "file": str(path),
        "raw": _analyze(raw),
        "exact": _analyze(exact),
    }


def diagnose_many(paths):
    reports = [
        diagnose_file(path)
        for path in paths
    ]

    raw = Counter()
    exact = Counter()

    raw_directions = Counter()
    exact_directions = Counter()

    for report in reports:
        raw.update(
            report["raw"].get("counts") or {}
        )

        exact.update(
            report["exact"].get("counts") or {}
        )

        raw_directions.update(
            report["raw"].get("directions") or {}
        )

        exact_directions.update(
            report["exact"].get("directions") or {}
        )

    return {
        "status": "COMPLETED",
        "stage": (
            "BROOKS_STRUCTURAL_ADVANCE_GATE_"
            "DIAGNOSTICS_V1"
        ),
        "deduplication": "EXACT_CANDLE_LAST_REVISION",
        "files": reports,
        "raw_counts": dict(raw),
        "exact_counts": dict(exact),
        "raw_directions": dict(raw_directions),
        "exact_directions": dict(exact_directions),
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
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

    report = diagnose_many(args.paths)

    if args.output:
        Path(args.output).write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print("status=", report["status"])
    print("stage=", report["stage"])

    print(
        "raw_counts=",
        json.dumps(
            report["raw_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "raw_directions=",
        json.dumps(
            report["raw_directions"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "exact_counts=",
        json.dumps(
            report["exact_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    print(
        "exact_directions=",
        json.dumps(
            report["exact_directions"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())