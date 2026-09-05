"""Auditoria EXACT_CANDLE para BROOKS_MAJOR_TREND_REVERSAL_V1.

Sequencia observacional:
    tendencia previa -> barra de reversao COUNTER_TREND -> mudanca estrutural
    explicita -> resposta explicita na nova direcao

Pesquisa somente. Nao altera Score, Risk, Decision, Alert ou execucao.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from research.price_action.brooks.major_trend_reversal import (
    BrooksMajorTrendReversalResearch,
    MajorTrendReversalObservation,
)

READY_STATUS = "CANDLE_EVIDENCE_READY"
MAX_SEQUENCE_WINDOW = 24


def _norm(value):
    return str(value or "").strip().upper()


def _candle_ts(row):
    evidence = row.get("candle_evidence") or {}
    raw = evidence.get("timestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _exact_identity_ready(payload):
    samples = payload.get("samples") or []
    if not samples:
        return False
    for row in samples:
        ev = row.get("candle_evidence") or {}
        if ev.get("status") != READY_STATUS or not ev.get("candle_id"):
            return False
    return True


def _last_revision_rows(payload):
    latest = {}
    order = []
    for row in payload.get("samples") or []:
        ev = row.get("candle_evidence") or {}
        if ev.get("status") != READY_STATUS or not ev.get("candle_id"):
            continue
        cid = ev["candle_id"]
        if cid not in latest:
            order.append(cid)
        latest[cid] = row
    rows = [latest[cid] for cid in order]
    rows.sort(key=lambda row: (_candle_ts(row) or datetime.min, str((row.get("candle_evidence") or {}).get("candle_id"))))
    return rows


def _pa(row):
    value = row.get("price_action") or {}
    return value if isinstance(value, dict) else {}


def _structure(row):
    value = row.get("structure") or {}
    return value if isinstance(value, dict) else {}


def _direction(value):
    value = _norm(value)
    if value in {"UP", "BUY", "BULL", "BULLISH"}:
        return "BUY"
    if value in {"DOWN", "SELL", "BEAR", "BEARISH"}:
        return "SELL"
    return "NONE"


def _reversal_start(row):
    pa = _pa(row)
    prior_trend = _direction(pa.get("trend"))
    reversal_direction = _direction(pa.get("brooks_reversal_direction"))
    quality = _norm(pa.get("brooks_reversal_quality"))
    context = _norm(pa.get("brooks_reversal_context"))
    if prior_trend == "NONE":
        return None
    expected = "SELL" if prior_trend == "BUY" else "BUY"
    if not bool(pa.get("brooks_reversal_candidate")):
        return None
    if reversal_direction != expected:
        return None
    if quality not in {"MODERATE", "STRONG"}:
        return None
    if context != "COUNTER_TREND":
        return None
    return prior_trend, expected, quality, context


def _structural_change(row, expected):
    structure = _structure(row)
    trend = _direction(structure.get("trend"))
    choch = bool(structure.get("choch"))
    if expected == "BUY":
        return bool(structure.get("bos_up")) or (choch and trend == "BUY")
    return bool(structure.get("bos_down")) or (choch and trend == "SELL")


def _structural_invalidation(row, expected):
    structure = _structure(row)
    if expected == "BUY":
        return bool(structure.get("bos_down"))
    return bool(structure.get("bos_up"))


def _response(row, expected):
    pa = _pa(row)
    phase = _norm(pa.get("brooks_signal_phase"))
    direction = _direction(pa.get("brooks_signal_direction"))
    return (
        phase in {"ENTRY_TRIGGERED", "FOLLOW_THROUGH"}
        and direction == expected
        and (bool(pa.get("brooks_entry_triggered")) or bool(pa.get("brooks_follow_through")))
    )


def audit_payload(payload, *, max_sequence_window=MAX_SEQUENCE_WINDOW):
    safety = {
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "hypothesis_freeze_allowed": False,
    }

    if not bool(payload.get("data_ready")):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["DATA_NOT_READY"], "sequences": [], **safety}
    if not _exact_identity_ready(payload):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["EXACT_CANDLE_IDENTITY_REQUIRED"], "sequences": [], **safety}

    rows = _last_revision_rows(payload)
    if any("brooks_reversal_context" not in _pa(row) for row in rows):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["REVERSAL_CONTEXT_EVIDENCE_REQUIRED"], "sequences": [], **safety}

    research = BrooksMajorTrendReversalResearch()
    sequences = []

    for start_idx, start_row in enumerate(rows):
        start = _reversal_start(start_row)
        if not start:
            continue
        prior_trend, expected, quality, context = start

        structural_idx = None
        invalidated_before_structure = False
        end_idx = min(len(rows), start_idx + 1 + int(max_sequence_window))
        for idx in range(start_idx + 1, end_idx):
            row = rows[idx]
            if _structural_invalidation(row, expected):
                invalidated_before_structure = True
                break
            if _structural_change(row, expected):
                structural_idx = idx
                break

        if structural_idx is None:
            sequences.append({
                "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
                "prior_trend": prior_trend,
                "direction": expected,
                "matched": False,
                "invalidated": invalidated_before_structure,
                "reason": "STRUCTURAL_INVALIDATION_BEFORE_CHANGE" if invalidated_before_structure else "STRUCTURAL_CHANGE_NOT_OBSERVED",
            })
            continue

        response_detected = False
        response_candle_id = None
        invalidated_after_structure = False
        for idx in range(structural_idx + 1, end_idx):
            row = rows[idx]
            if _structural_invalidation(row, expected):
                invalidated_after_structure = True
                break
            if _response(row, expected):
                response_detected = True
                response_candle_id = (row.get("candle_evidence") or {}).get("candle_id")
                break

        start_ev = start_row.get("candle_evidence") or {}
        observation = MajorTrendReversalObservation(
            prior_trend=prior_trend,
            reversal_candidate=True,
            reversal_direction=expected,
            reversal_quality=quality,
            reversal_context=context,
            structural_change=True,
            structural_change_direction=expected,
            response_detected=response_detected,
            structural_invalidation=invalidated_after_structure,
            candle_id=start_ev.get("candle_id"),
        )
        result = research.evaluate(observation)
        sequences.append({
            "start_candle_id": start_ev.get("candle_id"),
            "structural_change_candle_id": (rows[structural_idx].get("candle_evidence") or {}).get("candle_id"),
            "response_candle_id": response_candle_id,
            "prior_trend": prior_trend,
            **asdict(result),
        })

    return {
        "status": "AUDIT_COMPLETED",
        "deduplication": "EXACT_CANDLE_LAST_REVISION",
        "exact_candle_identity_available": True,
        "sequence_count": len(sequences),
        "matched_sequence_count": sum(1 for item in sequences if item.get("matched")),
        "sequences": sequences,
        **safety,
    }


def _session_interval(payload):
    rows = _last_revision_rows(payload)
    ts = [x for x in (_candle_ts(row) for row in rows) if x is not None]
    if not ts:
        return None
    return min(ts), max(ts)


def audit_sessions(payloads, *, max_sequence_window=MAX_SEQUENCE_WINDOW):
    accepted, rejected, intervals = [], [], []
    for index, payload in enumerate(payloads):
        interval = _session_interval(payload)
        if interval is None:
            rejected.append({"session_index": index, "reason": "SESSION_INTERVAL_UNAVAILABLE"})
            continue
        start, end = interval
        if any(start <= old_end and end >= old_start for old_start, old_end in intervals):
            rejected.append({"session_index": index, "reason": "TEMPORAL_OVERLAP"})
            continue
        result = audit_payload(payload, max_sequence_window=max_sequence_window)
        if result.get("status") != "AUDIT_COMPLETED":
            rejected.append({"session_index": index, "reason": "SESSION_NOT_ELIGIBLE", "audit": result})
            continue
        intervals.append(interval)
        accepted.append({"session_index": index, "audit": result})
    return {
        "status": "MULTI_SESSION_AUDIT_COMPLETED",
        "accepted_session_count": len(accepted),
        "rejected_session_count": len(rejected),
        "accepted_sessions": accepted,
        "rejected_sessions": rejected,
        "matched_sequence_count": sum(item["audit"].get("matched_sequence_count", 0) for item in accepted),
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "hypothesis_freeze_allowed": False,
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Audita BROOKS_MAJOR_TREND_REVERSAL_V1 por EXACT_CANDLE.")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    parser.add_argument("--max-sequence-window", type=int, default=MAX_SEQUENCE_WINDOW)
    args = parser.parse_args(argv)
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.paths]
    result = audit_sessions(payloads, max_sequence_window=args.max_sequence_window) if len(payloads) > 1 else audit_payload(payloads[0], max_sequence_window=args.max_sequence_window)
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
