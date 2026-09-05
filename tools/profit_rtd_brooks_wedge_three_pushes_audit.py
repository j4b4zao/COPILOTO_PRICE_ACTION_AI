"""Auditoria EXACT_CANDLE para BROOKS_WEDGE_THREE_PUSHES_V1.

Sequencia observacional:
    three pushes registrados -> reversao oposta MODERATE/STRONG ->
    mudanca estrutural alinhada -> resposta explicita.

Pesquisa somente. Nao altera Score, Risk, Decision, Alert ou execucao.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from research.price_action.brooks.wedge_three_pushes import (
    BrooksWedgeThreePushesResearch,
    WedgeThreePushesObservation,
)

READY_STATUS = "CANDLE_EVIDENCE_READY"
MAX_SEQUENCE_WINDOW = 24


def _norm(value):
    return str(value or "").strip().upper()


def _direction(value):
    value = _norm(value)
    if value in {"UP", "BUY", "BULL", "BULLISH"}:
        return "BUY"
    if value in {"DOWN", "SELL", "BEAR", "BEARISH"}:
        return "SELL"
    return "NONE"


def _candle_ts(row):
    ev = row.get("candle_evidence") or {}
    raw = ev.get("timestamp")
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
    return all(
        (row.get("candle_evidence") or {}).get("status") == READY_STATUS
        and bool((row.get("candle_evidence") or {}).get("candle_id"))
        for row in samples
    )


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


def _push_start(row):
    pa = _pa(row)
    if not bool(pa.get("brooks_three_pushes_detected")):
        return None
    push = _direction(pa.get("brooks_three_pushes_direction"))
    indices = pa.get("brooks_three_pushes_indices")
    prices = pa.get("brooks_three_pushes_prices")
    if push == "NONE":
        return None
    if not isinstance(indices, list) or len(indices) != 3:
        return None
    if not isinstance(prices, list) or len(prices) != 3:
        return None
    expected = "SELL" if push == "BUY" else "BUY"
    return push, expected


def _reversal(row, expected):
    pa = _pa(row)
    return (
        bool(pa.get("brooks_reversal_candidate"))
        and _direction(pa.get("brooks_reversal_direction")) == expected
        and _norm(pa.get("brooks_reversal_quality")) in {"MODERATE", "STRONG"}
    )


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
    required = (
        "brooks_three_pushes_detected",
        "brooks_three_pushes_direction",
        "brooks_three_pushes_indices",
        "brooks_three_pushes_prices",
    )
    if any(any(key not in _pa(row) for key in required) for row in rows):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["THREE_PUSHES_EVIDENCE_REQUIRED"], "sequences": [], **safety}

    research = BrooksWedgeThreePushesResearch()
    sequences = []

    for start_idx, start_row in enumerate(rows):
        start = _push_start(start_row)
        if not start:
            continue
        push, expected = start
        end_idx = min(len(rows), start_idx + 1 + int(max_sequence_window))

        reversal_idx = None
        invalidated = False
        for idx in range(start_idx + 1, end_idx):
            if _structural_invalidation(rows[idx], expected):
                invalidated = True
                break
            if _reversal(rows[idx], expected):
                reversal_idx = idx
                break

        if reversal_idx is None:
            sequences.append({
                "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
                "push_direction": push,
                "direction": expected,
                "matched": False,
                "invalidated": invalidated,
                "reason": "STRUCTURAL_INVALIDATION_BEFORE_REVERSAL" if invalidated else "REVERSAL_NOT_OBSERVED",
            })
            continue

        structural_idx = None
        invalidated = False
        for idx in range(reversal_idx + 1, end_idx):
            if _structural_invalidation(rows[idx], expected):
                invalidated = True
                break
            if _structural_change(rows[idx], expected):
                structural_idx = idx
                break

        if structural_idx is None:
            sequences.append({
                "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
                "reversal_candle_id": (rows[reversal_idx].get("candle_evidence") or {}).get("candle_id"),
                "push_direction": push,
                "direction": expected,
                "matched": False,
                "invalidated": invalidated,
                "reason": "STRUCTURAL_INVALIDATION_BEFORE_CHANGE" if invalidated else "STRUCTURAL_CHANGE_NOT_OBSERVED",
            })
            continue

        response_detected = False
        response_candle_id = None
        invalidated = False
        for idx in range(structural_idx + 1, end_idx):
            if _structural_invalidation(rows[idx], expected):
                invalidated = True
                break
            if _response(rows[idx], expected):
                response_detected = True
                response_candle_id = (rows[idx].get("candle_evidence") or {}).get("candle_id")
                break

        reversal_pa = _pa(rows[reversal_idx])
        observation = WedgeThreePushesObservation(
            three_pushes_detected=True,
            push_direction=push,
            reversal_candidate=True,
            reversal_direction=expected,
            reversal_quality=_norm(reversal_pa.get("brooks_reversal_quality")),
            structural_change=True,
            structural_change_direction=expected,
            response_detected=response_detected,
            structural_invalidation=invalidated,
            candle_id=(start_row.get("candle_evidence") or {}).get("candle_id"),
        )
        result = research.evaluate(observation)
        sequences.append({
            "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
            "reversal_candle_id": (rows[reversal_idx].get("candle_evidence") or {}).get("candle_id"),
            "structural_change_candle_id": (rows[structural_idx].get("candle_evidence") or {}).get("candle_id"),
            "response_candle_id": response_candle_id,
            "push_direction": push,
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
    ts = [value for value in (_candle_ts(row) for row in rows) if value is not None]
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
    parser = argparse.ArgumentParser(description="Audita BROOKS_WEDGE_THREE_PUSHES_V1 por EXACT_CANDLE.")
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
