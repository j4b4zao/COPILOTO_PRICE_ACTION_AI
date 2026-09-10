"""Auditoria Brooks breakout-pullback com memoria observacional do nivel.

Extende a auditoria existente sem alterar BreakoutDynamics. O nivel de
rompimento precisa ter sido explicitamente capturado no candle de breakout.
A partir desse nivel, candles posteriores podem provar reteste/defesa dentro
da janela de pesquisa.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.price_action.brooks.breakout_pullback import (
    BreakoutPullbackObservation,
    BrooksBreakoutPullbackResearch,
)
from tools.profit_rtd_brooks_breakout_pullback_audit import (
    _breakout_explicit,
    _direction_for_trend,
    _exact_ready,
    _last_revision_per_candle,
    _producer_phase_coverage,
    _resumption_explicit,
    _rows,
    _safety,
    _structure_invalidated,
    _trend,
)
from tools.profit_rtd_price_action_evidence_audit import _session_interval


def _explicit_breakout_level(row):
    pa = row.get("price_action") or {}
    try:
        level = float(pa.get("brooks_breakout_level"))
    except (TypeError, ValueError):
        return None
    return level if level != 0.0 else None


def _remembered_test(row, direction, level):
    """Prova reteste/defesa usando somente OHLC observado e nivel capturado."""
    if level is None:
        return False, None, False, None

    candle = row.get("candle_evidence") or {}
    try:
        high = float(candle.get("high"))
        low = float(candle.get("low"))
        close = float(candle.get("close"))
    except (TypeError, ValueError):
        return False, None, False, None

    if direction == "BUY" and low <= level <= close:
        return (
            True,
            "RESEARCH_BREAKOUT_MEMORY_LEVEL_RETEST",
            True,
            "RESEARCH_BREAKOUT_MEMORY_LEVEL_HELD",
        )
    if direction == "SELL" and high >= level >= close:
        return (
            True,
            "RESEARCH_BREAKOUT_MEMORY_LEVEL_RETEST",
            True,
            "RESEARCH_BREAKOUT_MEMORY_LEVEL_HELD",
        )
    return False, None, False, None


def _producer_or_memory_test(row, direction, level):
    pa = row.get("price_action") or {}
    phase = str(pa.get("brooks_breakout_phase") or "").strip().upper()
    raw_direction = str(pa.get("brooks_breakout_direction") or "").strip().upper()
    aligned = (
        direction == "BUY" and raw_direction in {"BUY", "UP", "BULL", "BULLISH"}
    ) or (
        direction == "SELL" and raw_direction in {"SELL", "DOWN", "BEAR", "BEARISH"}
    )
    if phase == "BREAKOUT_TESTED" and aligned:
        return (
            True,
            "PA_BROOKS_BREAKOUT_TESTED",
            True,
            "PA_BROOKS_BREAKOUT_TEST_HELD",
        )
    return _remembered_test(row, direction, level)


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

        breakout_level = _explicit_breakout_level(breakout_row)
        evidence = {
            "breakout": {
                "candle_id": breakout_row["candle_evidence"]["candle_id"],
                "source": breakout_source,
                "level": breakout_level,
            }
        }
        pullback = rejection = resumption = invalidated = False

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
                pullback, p_source, rejection, r_source = _producer_or_memory_test(
                    row, direction, breakout_level
                )
                if pullback:
                    candle_id = row["candle_evidence"]["candle_id"]
                    evidence["pullback"] = {"candle_id": candle_id, "source": p_source}
                    evidence["rejection"] = {"candle_id": candle_id, "source": r_source}
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
        (sequences if result.matched else incomplete).append(item)

    complete = len(sequences)
    return {
        "session": source.name,
        "status": "MATCHES_OBSERVED" if complete else "INSUFFICIENT_SEQUENCE_EVIDENCE",
        "exact_candles": len(rows),
        "complete_sequences": complete,
        "incomplete_candidates": len(incomplete),
        "sequences": sequences,
        "incomplete": incomplete,
        "producer_phase_coverage": {
            **_producer_phase_coverage(rows),
            "research_breakout_memory": True,
            "research_breakout_memory_max_sequence_candles": int(max_sequence_candles),
        },
        "reasons": [] if complete else ["NO_COMPLETE_EXPLICIT_BREAKOUT_PULLBACK_SEQUENCE"],
        **_safety(),
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
            prior_name
            for prior_name, prior_interval in accepted_intervals
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
        if interval is not None and result.get("status") in {
            "MATCHES_OBSERVED", "INSUFFICIENT_SEQUENCE_EVIDENCE"
        }:
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
            if complete else ["NO_COMPLETE_EXPLICIT_BREAKOUT_PULLBACK_SEQUENCE"]
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
