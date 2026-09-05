"""Auditoria EXACT_CANDLE de BROOKS_TREND_PULLBACK_V1.

Pesquisa apenas. Nao altera Score/Risk/Decision/Alert/execucao.
Exige evidencia explicita de FirstPullbackSequenceDynamics capturada no JSON.
Nao reconstrói estagios ausentes a partir de retorno futuro.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from enums.trend import Trend
from research.price_action.brooks.trend_pullback import (
    BrooksTrendPullbackResearch,
    TrendPullbackObservation,
)
from tools.profit_rtd_price_action_evidence_audit import _session_interval

_REQUIRED_PULLBACK_FIELDS = {
    "brooks_first_pullback_valid",
    "brooks_first_pullback_direction",
    "brooks_first_pullback_stage",
    "brooks_first_pullback_stage_index",
    "brooks_first_pullback_continuation_bias",
    "brooks_first_pullback_reversal_risk",
    "brooks_first_pullback_trading_range_transition",
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


def _rows(payload):
    if not isinstance(payload, dict) or payload.get("data_ready") is not True:
        return []
    rows = payload.get("samples")
    return rows if isinstance(rows, list) else []


def _exact_ready(row):
    ev = row.get("candle_evidence") if isinstance(row, dict) else None
    return isinstance(ev, dict) and ev.get("status") == "CANDLE_EVIDENCE_READY" and bool(ev.get("candle_id"))


def _dedup(rows):
    latest, order = {}, []
    for row in rows:
        if not _exact_ready(row):
            continue
        cid = row["candle_evidence"]["candle_id"]
        if cid not in latest:
            order.append(cid)
        latest[cid] = row
    return [latest[cid] for cid in order]


def _text(value):
    return str(value or "").strip().upper()


def _trend(row):
    value = _text((row.get("structure") or {}).get("trend"))
    try:
        return Trend(value)
    except ValueError:
        return Trend.UNKNOWN


def _expected_direction(trend):
    if trend == Trend.UP:
        return "BUY"
    if trend == Trend.DOWN:
        return "SELL"
    return "NONE"


def _aligned(value, direction):
    value = _text(value)
    return value in ({"BUY", "UP", "BULL", "BULLISH"} if direction == "BUY" else {"SELL", "DOWN", "BEAR", "BEARISH"})


def _pullback_fields_present(row):
    pa = row.get("price_action") or {}
    return _REQUIRED_PULLBACK_FIELDS.issubset(pa.keys())


def _resumption_explicit(row, direction):
    pa = row.get("price_action") or {}
    if not _aligned(pa.get("brooks_signal_direction"), direction):
        return False, None
    phase = _text(pa.get("brooks_signal_phase"))
    if pa.get("brooks_follow_through") is True and phase == "FOLLOW_THROUGH":
        return True, "PA_BROOKS_SIGNAL_FOLLOW_THROUGH"
    if pa.get("brooks_entry_triggered") is True and phase in {"ENTRY_TRIGGERED", "FOLLOW_THROUGH"}:
        return True, "PA_BROOKS_SIGNAL_ENTRY_TRIGGERED"
    return False, None


def _invalidated(row, direction):
    st = row.get("structure") or {}
    if st.get("choch") is not True:
        return False
    trend = _text(st.get("trend"))
    return (direction == "BUY" and trend == "DOWN") or (direction == "SELL" and trend == "UP")


def audit_session(path, *, max_sequence_candles=20):
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    raw = _rows(payload)
    if not raw:
        return {"session": source.name, "status": "SESSION_NOT_ELIGIBLE", "reasons": ["DATA_READY_SESSION_REQUIRED"], **_safety()}
    if not all(_exact_ready(row) for row in raw):
        return {"session": source.name, "status": "SESSION_NOT_ELIGIBLE", "reasons": ["EXACT_CANDLE_IDENTITY_REQUIRED"], **_safety()}

    rows = _dedup(raw)
    coverage = sum(_pullback_fields_present(row) for row in rows)
    if coverage != len(rows):
        return {
            "session": source.name,
            "status": "SESSION_NOT_ELIGIBLE",
            "exact_candles": len(rows),
            "pullback_evidence_rows": coverage,
            "missing_pullback_evidence_rows": len(rows) - coverage,
            "reasons": ["FIRST_PULLBACK_SEQUENCE_EVIDENCE_REQUIRED"],
            **_safety(),
        }

    classifier = BrooksTrendPullbackResearch()
    complete, incomplete = [], []
    for i, row in enumerate(rows):
        trend = _trend(row)
        direction = _expected_direction(trend)
        if direction == "NONE":
            continue
        pa = row.get("price_action") or {}
        if pa.get("brooks_first_pullback_valid") is not True:
            continue

        pullback_direction = _text(pa.get("brooks_first_pullback_direction"))
        stage = str(pa.get("brooks_first_pullback_stage") or "NO_SEQUENCE")
        stage_index = int(pa.get("brooks_first_pullback_stage_index") or 0)
        continuation_bias = pa.get("brooks_first_pullback_continuation_bias") is True
        reversal_risk = pa.get("brooks_first_pullback_reversal_risk") is True
        range_transition = pa.get("brooks_first_pullback_trading_range_transition") is True
        resumption = False
        structural_invalidation = False
        evidence = {
            "pullback": {
                "candle_id": row["candle_evidence"]["candle_id"],
                "stage": stage,
                "stage_index": stage_index,
                "source": "FIRST_PULLBACK_SEQUENCE_DYNAMICS",
            }
        }
        end = min(len(rows), i + 1 + int(max_sequence_candles))
        for later in rows[i + 1:end]:
            if _invalidated(later, direction):
                structural_invalidation = True
                evidence["invalidation"] = {"candle_id": later["candle_evidence"]["candle_id"], "source": "OPPOSITE_CHOCH"}
                break
            resumption, source_name = _resumption_explicit(later, direction)
            if resumption:
                evidence["resumption"] = {"candle_id": later["candle_evidence"]["candle_id"], "source": source_name}
                break

        result = classifier.evaluate(TrendPullbackObservation(
            trend=trend,
            pullback_detected=True,
            pullback_direction=pullback_direction,
            pullback_stage=stage,
            pullback_stage_index=stage_index,
            continuation_bias=continuation_bias,
            reversal_risk=reversal_risk,
            resumption_detected=resumption,
            structural_invalidation=structural_invalidation,
            trading_range_transition=range_transition,
            candle_id=row["candle_evidence"]["candle_id"],
        ))
        item = {
            "direction": direction,
            "matched": result.matched,
            "invalidated": result.invalidated,
            "sequence_complete": result.sequence_complete,
            "reasons": list(result.reasons),
            "evidence": evidence,
        }
        (complete if result.matched else incomplete).append(item)

    return {
        "session": source.name,
        "status": "MATCHES_OBSERVED" if complete else "INSUFFICIENT_SEQUENCE_EVIDENCE",
        "exact_candles": len(rows),
        "pullback_evidence_rows": coverage,
        "complete_sequences": len(complete),
        "incomplete_candidates": len(incomplete),
        "sequences": complete,
        "incomplete": incomplete,
        "reasons": [] if complete else ["NO_COMPLETE_EXPLICIT_TREND_PULLBACK_SEQUENCE"],
        **_safety(),
    }


def audit(paths, *, max_sequence_candles=20):
    candidates = []
    for raw in paths:
        path = Path(raw)
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates.append((path, _session_interval(_rows(payload))))
    candidates.sort(key=lambda x: (x[1] is None, x[1][0] if x[1] else float("inf"), x[0].name))

    sessions, accepted = [], []
    for path, interval in candidates:
        overlap = next((name for name, prior in accepted if interval and interval[0] <= prior[1] and prior[0] <= interval[1]), None)
        if overlap:
            sessions.append({"session": path.name, "status": "SESSION_NOT_ELIGIBLE", "reasons": ["TEMPORAL_OVERLAP"], "overlaps_with": overlap, **_safety()})
            continue
        result = audit_session(path, max_sequence_candles=max_sequence_candles)
        sessions.append(result)
        if interval and result.get("status") in {"MATCHES_OBSERVED", "INSUFFICIENT_SEQUENCE_EVIDENCE"}:
            accepted.append((path.name, interval))

    total = sum(x.get("complete_sequences", 0) for x in sessions)
    eligible = sum(x.get("status") in {"MATCHES_OBSERVED", "INSUFFICIENT_SEQUENCE_EVIDENCE"} for x in sessions)
    return {
        "status": "MATCHES_OBSERVED" if total else "MORE_EVIDENCE_REQUIRED",
        "eligible_sessions": eligible,
        "complete_sequences": total,
        "sessions": sessions,
        "hypothesis_freeze_allowed": False,
        "reasons": ["COMPLETE_EXPLICIT_SEQUENCE_OBSERVED_RESEARCH_ONLY"] if total else ["NO_COMPLETE_EXPLICIT_TREND_PULLBACK_SEQUENCE"],
        **_safety(),
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="+")
    p.add_argument("--max-sequence-candles", type=int, default=20)
    p.add_argument("--output")
    a = p.parse_args(argv)
    result = audit(a.paths, max_sequence_candles=a.max_sequence_candles)
    text = json.dumps(result, indent=2, sort_keys=True)
    if a.output:
        target = Path(a.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
