"""Auditoria observacional de BROOKS_BREAKOUT_PULLBACK_V1 em sessoes EXACT_CANDLE.

Este modulo NAO cria sinais operacionais. Ele apenas procura uma sequencia
explicitamente demonstravel nos campos ja capturados pelos JSONs RC54:

    tendencia -> breakout -> pullback -> rejeicao -> retomada

Nao ha inferencia por retorno futuro e nenhum candle isolado e convertido em
setup. Quando a sequencia nao pode ser provada, o resultado permanece como
evidencia insuficiente.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from enums.trend import Trend
from research.price_action.brooks.breakout_pullback import (
    BreakoutPullbackObservation,
    BrooksBreakoutPullbackResearch,
)
from tools.profit_rtd_price_action_evidence_audit import _session_interval


def _rows(payload):
    if not isinstance(payload, dict) or payload.get("data_ready") is not True:
        return []
    rows = payload.get("samples")
    return rows if isinstance(rows, list) else []


def _exact_ready(row):
    evidence = row.get("candle_evidence") if isinstance(row, dict) else None
    return (
        isinstance(evidence, dict)
        and evidence.get("status") == "CANDLE_EVIDENCE_READY"
        and bool(evidence.get("candle_id"))
    )


def _last_revision_per_candle(rows):
    latest = {}
    order = []
    for row in rows:
        if not _exact_ready(row):
            continue
        candle_id = row["candle_evidence"]["candle_id"]
        if candle_id not in latest:
            order.append(candle_id)
        latest[candle_id] = row
    return [latest[candle_id] for candle_id in order]


def _text(value):
    return str(value or "").strip().upper()


def _trend(row):
    value = _text((row.get("structure") or {}).get("trend"))
    try:
        return Trend(value)
    except ValueError:
        return Trend.UNKNOWN


def _direction_for_trend(trend):
    if trend == Trend.UP:
        return "BUY"
    if trend == Trend.DOWN:
        return "SELL"
    return "NONE"


def _breakout_explicit(row, direction):
    structure = row.get("structure") or {}
    pa = row.get("price_action") or {}
    if direction == "BUY" and structure.get("bos_up") is True:
        return True, "STRUCTURE_BOS_UP"
    if direction == "SELL" and structure.get("bos_down") is True:
        return True, "STRUCTURE_BOS_DOWN"

    phase = _text(pa.get("brooks_breakout_phase"))
    pa_direction = _text(pa.get("brooks_breakout_direction"))
    aligned = (
        pa_direction in {"BUY", "UP", "BULL", "BULLISH"}
        if direction == "BUY"
        else pa_direction in {"SELL", "DOWN", "BEAR", "BEARISH"}
    )
    if aligned and "BREAKOUT" in phase and "FAIL" not in phase:
        return True, "PA_BROOKS_BREAKOUT_PHASE"
    return False, None


def _pullback_explicit(row, direction):
    pa = row.get("price_action") or {}
    phase = _text(pa.get("brooks_signal_phase"))
    signal_direction = _text(pa.get("brooks_signal_direction"))
    expected = (
        {"BUY", "UP", "BULL", "BULLISH"}
        if direction == "BUY"
        else {"SELL", "DOWN", "BEAR", "BEARISH"}
    )
    if "PULLBACK" in phase and signal_direction in expected | {"", "NONE"}:
        return True, "PA_BROOKS_SIGNAL_PULLBACK"
    return False, None


def _rejection_explicit(row, direction):
    pa = row.get("price_action") or {}
    phase = _text(pa.get("brooks_signal_phase"))
    signal_direction = _text(pa.get("brooks_signal_direction"))
    expected = (
        {"BUY", "UP", "BULL", "BULLISH"}
        if direction == "BUY"
        else {"SELL", "DOWN", "BEAR", "BEARISH"}
    )
    if "REJECT" in phase and signal_direction in expected | {"", "NONE"}:
        return True, "PA_BROOKS_SIGNAL_REJECTION"
    if pa.get("brooks_entry_triggered") is True and signal_direction in expected:
        return True, "PA_BROOKS_ENTRY_TRIGGERED"
    return False, None


def _resumption_explicit(row, direction):
    pa = row.get("price_action") or {}
    breakout_direction = _text(pa.get("brooks_breakout_direction"))
    signal_direction = _text(pa.get("brooks_signal_direction"))
    expected = (
        {"BUY", "UP", "BULL", "BULLISH"}
        if direction == "BUY"
        else {"SELL", "DOWN", "BEAR", "BEARISH"}
    )
    if pa.get("brooks_follow_through") is True and signal_direction in expected:
        return True, "PA_BROOKS_FOLLOW_THROUGH"
    if pa.get("brooks_breakout_follow_through") is True and breakout_direction in expected:
        return True, "PA_BROOKS_BREAKOUT_FOLLOW_THROUGH"
    return False, None


def _structure_invalidated(row, direction):
    structure = row.get("structure") or {}
    if direction == "BUY":
        return structure.get("choch") is True and _text(structure.get("trend")) == "DOWN"
    if direction == "SELL":
        return structure.get("choch") is True and _text(structure.get("trend")) == "UP"
    return False


def audit_session(path, *, max_sequence_candles=20):
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    raw_rows = _rows(payload)

    if not raw_rows:
        return {
            "session": source.name,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["DATA_READY_SESSION_REQUIRED"],
            **_safety(),
        }
    if not all(_exact_ready(row) for row in raw_rows):
        return {
            "session": source.name,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["EXACT_CANDLE_IDENTITY_REQUIRED"],
            **_safety(),
        }

    rows = _last_revision_per_candle(raw_rows)
    classifier = BrooksBreakoutPullbackResearch()
    sequences = []
    incomplete = []

    for index, breakout_row in enumerate(rows):
        trend = _trend(breakout_row)
        direction = _direction_for_trend(trend)
        if direction == "NONE":
            continue
        breakout_detected, breakout_source = _breakout_explicit(breakout_row, direction)
        if not breakout_detected:
            continue

        evidence = {
            "breakout": {
                "candle_id": breakout_row["candle_evidence"]["candle_id"],
                "source": breakout_source,
            }
        }
        pullback = rejection = resumption = False
        invalidated = False

        end = min(len(rows), index + 1 + int(max_sequence_candles))
        for row in rows[index + 1:end]:
            if _structure_invalidated(row, direction):
                invalidated = True
                evidence["invalidation"] = {
                    "candle_id": row["candle_evidence"]["candle_id"],
                    "source": "OPPOSITE_CHOCH",
                }
                break

            if not pullback:
                pullback, source_name = _pullback_explicit(row, direction)
                if pullback:
                    evidence["pullback"] = {
                        "candle_id": row["candle_evidence"]["candle_id"],
                        "source": source_name,
                    }
                continue

            if not rejection:
                rejection, source_name = _rejection_explicit(row, direction)
                if rejection:
                    evidence["rejection"] = {
                        "candle_id": row["candle_evidence"]["candle_id"],
                        "source": source_name,
                    }
                continue

            if not resumption:
                resumption, source_name = _resumption_explicit(row, direction)
                if resumption:
                    evidence["resumption"] = {
                        "candle_id": row["candle_evidence"]["candle_id"],
                        "source": source_name,
                    }
                    break

        observation = BreakoutPullbackObservation(
            trend=trend,
            breakout_direction=direction,
            breakout_detected=breakout_detected,
            pullback_detected=pullback,
            rejection_detected=rejection,
            resumption_detected=resumption,
            structural_level_lost=invalidated,
            candle_id=breakout_row["candle_evidence"]["candle_id"],
        )
        result = classifier.evaluate(observation)
        item = {
            "direction": direction,
            "matched": result.matched,
            "invalidated": result.invalidated,
            "sequence_complete": result.sequence_complete,
            "reasons": list(result.reasons),
            "evidence": evidence,
        }
        if result.matched:
            sequences.append(item)
        else:
            incomplete.append(item)

    status = "MATCHES_OBSERVED" if sequences else "INSUFFICIENT_SEQUENCE_EVIDENCE"
    reasons = [] if sequences else ["NO_COMPLETE_EXPLICIT_BREAKOUT_PULLBACK_SEQUENCE"]
    return {
        "session": source.name,
        "status": status,
        "exact_candles": len(rows),
        "complete_sequences": len(sequences),
        "incomplete_candidates": len(incomplete),
        "sequences": sequences,
        "incomplete": incomplete,
        "reasons": reasons,
        **_safety(),
    }


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
    }


def audit(paths, *, max_sequence_candles=20):
    candidates = []
    for raw_path in paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates.append((path, _session_interval(_rows(payload))))
    candidates.sort(key=lambda item: (
        item[1] is None,
        item[1][0] if item[1] is not None else float("inf"),
        item[0].name,
    ))

    sessions = []
    accepted_intervals = []
    for path, interval in candidates:
        overlap = next((
            prior_name for prior_name, prior_interval in accepted_intervals
            if interval is not None
            and interval[0] <= prior_interval[1]
            and prior_interval[0] <= interval[1]
        ), None)
        if overlap is not None:
            sessions.append({
                "session": path.name,
                "status": "SESSION_NOT_ELIGIBLE",
                "reasons": ["TEMPORAL_OVERLAP"],
                "overlaps_with": overlap,
                **_safety(),
            })
            continue
        result = audit_session(path, max_sequence_candles=max_sequence_candles)
        sessions.append(result)
        if (
            interval is not None
            and result.get("status") in {"MATCHES_OBSERVED", "INSUFFICIENT_SEQUENCE_EVIDENCE"}
        ):
            accepted_intervals.append((path.name, interval))
    complete = sum(item.get("complete_sequences", 0) for item in sessions)
    eligible_sessions = sum(
        item.get("status") in {"MATCHES_OBSERVED", "INSUFFICIENT_SEQUENCE_EVIDENCE"}
        for item in sessions
    )
    return {
        "status": "MATCHES_OBSERVED" if complete else "MORE_EVIDENCE_REQUIRED",
        "eligible_sessions": eligible_sessions,
        "sessions": sessions,
        "complete_sequences": complete,
        "hypothesis_freeze_allowed": False,
        "reasons": (
            ["COMPLETE_EXPLICIT_SEQUENCE_OBSERVED_RESEARCH_ONLY"]
            if complete
            else ["NO_COMPLETE_EXPLICIT_BREAKOUT_PULLBACK_SEQUENCE"]
        ),
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--max-sequence-candles", type=int, default=20)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    result = audit(args.paths, max_sequence_candles=args.max_sequence_candles)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
