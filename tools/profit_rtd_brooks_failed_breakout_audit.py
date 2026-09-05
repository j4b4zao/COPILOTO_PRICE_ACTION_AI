"""Auditoria EXACT_CANDLE para BROOKS_FAILED_BREAKOUT_V1.

Pesquisa observacional somente. Nao altera Score, Risk, Decision, Alert ou execucao.

Sequencia aceita:
    BREAKOUT_PENDING -> BREAKOUT_FAILED -> resposta oposta explicita

Regras:
- exige candle_evidence exato e data_ready;
- usa a ultima revisao de cada candle_id;
- nao infere falha por retorno futuro;
- rejeita sessoes temporalmente sobrepostas no modo multi-session;
- mantem hypothesis_freeze_allowed=False.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from research.price_action.brooks.failed_breakout import (
    BrooksFailedBreakoutResearch,
    FailedBreakoutObservation,
)


READY_STATUS = "CANDLE_EVIDENCE_READY"
MAX_SEQUENCE_WINDOW = 20


def _norm(value):
    return str(value or "").strip().upper()


def _direction(value):
    value = _norm(value)
    if value in {"UP", "BUY", "BULL", "BULLISH"}:
        return "UP"
    if value in {"DOWN", "SELL", "BEAR", "BEARISH"}:
        return "DOWN"
    return "NONE"


def _candle_ts(row):
    evidence = row.get("candle_evidence") or {}
    raw = evidence.get("timestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _last_revision_rows(payload):
    latest = {}
    order = []
    for row in payload.get("samples") or []:
        evidence = row.get("candle_evidence") or {}
        if evidence.get("status") != READY_STATUS or not evidence.get("candle_id"):
            continue
        cid = evidence["candle_id"]
        if cid not in latest:
            order.append(cid)
        latest[cid] = row
    rows = [latest[cid] for cid in order]
    rows.sort(key=lambda row: (_candle_ts(row) or datetime.min, str((row.get("candle_evidence") or {}).get("candle_id"))))
    return rows


def _exact_identity_ready(payload):
    samples = payload.get("samples") or []
    if not samples:
        return False
    for row in samples:
        evidence = row.get("candle_evidence") or {}
        if evidence.get("status") != READY_STATUS or not evidence.get("candle_id"):
            return False
    return True


def _pa(row):
    value = row.get("price_action") or {}
    return value if isinstance(value, dict) else {}


def _structure(row):
    value = row.get("structure") or {}
    return value if isinstance(value, dict) else {}


def _is_breakout_start(row):
    pa = _pa(row)
    phase = _norm(pa.get("brooks_breakout_phase"))
    direction = _norm(pa.get("brooks_breakout_direction"))
    if phase != "BREAKOUT_PENDING" or direction not in {"UP", "DOWN"}:
        return None
    return direction


def _is_failure(row, breakout_direction):
    pa = _pa(row)
    return (
        _norm(pa.get("brooks_breakout_phase")) == "BREAKOUT_FAILED"
        and bool(pa.get("brooks_breakout_failed"))
        and _norm(pa.get("brooks_breakout_direction")) == breakout_direction
    )


def _opposite_response(row, breakout_direction):
    pa = _pa(row)
    signal_phase = _norm(pa.get("brooks_signal_phase"))
    signal_direction = _norm(pa.get("brooks_signal_direction"))
    expected = "SELL" if breakout_direction == "UP" else "BUY"
    explicit = (
        signal_phase in {"ENTRY_TRIGGERED", "FOLLOW_THROUGH"}
        and signal_direction == expected
        and (bool(pa.get("brooks_entry_triggered")) or bool(pa.get("brooks_follow_through")))
    )
    return explicit, expected


def _opposite_choch(row, breakout_direction):
    """Detecta CHOCH contrario usando o contrato real do RC17.

    ``structure.choch`` e booleano. A direcao e inferida pela tendencia
    estrutural exposta no mesmo snapshot, a mesma convencao usada pelo
    auditor de Major Trend Reversal.
    """
    structure = _structure(row)
    if not bool(structure.get("choch")):
        return False
    trend = _direction(structure.get("trend"))
    if breakout_direction == "UP":
        return trend == "DOWN"
    if breakout_direction == "DOWN":
        return trend == "UP"
    return False


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
    research = BrooksFailedBreakoutResearch()
    sequences = []

    for start_idx, start_row in enumerate(rows):
        breakout_direction = _is_breakout_start(start_row)
        if not breakout_direction:
            continue

        failure_idx = None
        invalidated = False
        for idx in range(start_idx + 1, min(len(rows), start_idx + 1 + int(max_sequence_window))):
            row = rows[idx]
            if _opposite_choch(row, breakout_direction):
                invalidated = True
                break
            if _is_failure(row, breakout_direction):
                failure_idx = idx
                break

        if failure_idx is None:
            sequences.append({
                "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
                "breakout_direction": breakout_direction,
                "matched": False,
                "invalidated": invalidated,
                "reason": "STRUCTURAL_INVALIDATION_BEFORE_FAILURE" if invalidated else "BREAKOUT_FAILURE_NOT_OBSERVED",
            })
            continue

        response_detected = False
        response_candle_id = None
        response_direction = "NONE"
        structural_invalidation = False
        for idx in range(failure_idx + 1, min(len(rows), start_idx + 1 + int(max_sequence_window))):
            row = rows[idx]
            if _opposite_choch(row, breakout_direction):
                structural_invalidation = True
                break
            response_detected, response_direction = _opposite_response(row, breakout_direction)
            if response_detected:
                response_candle_id = (row.get("candle_evidence") or {}).get("candle_id")
                break

        failure_row = rows[failure_idx]
        observation = FailedBreakoutObservation(
            breakout_direction=breakout_direction,
            breakout_detected=True,
            failure_detected=True,
            failure_direction=("SELL" if breakout_direction == "UP" else "BUY"),
            opposite_response_detected=response_detected,
            structural_invalidation=structural_invalidation,
            candle_id=(failure_row.get("candle_evidence") or {}).get("candle_id"),
        )
        result = research.evaluate(observation)
        sequences.append({
            "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
            "failure_candle_id": (failure_row.get("candle_evidence") or {}).get("candle_id"),
            "response_candle_id": response_candle_id,
            "breakout_direction": breakout_direction,
            "response_direction": response_direction,
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
    timestamps = [ts for ts in (_candle_ts(row) for row in rows) if ts is not None]
    if not timestamps:
        return None
    return min(timestamps), max(timestamps)


def audit_sessions(payloads, *, max_sequence_window=MAX_SEQUENCE_WINDOW):
    accepted = []
    rejected = []
    intervals = []

    for index, payload in enumerate(payloads):
        interval = _session_interval(payload)
        if interval is None:
            rejected.append({"session_index": index, "reason": "SESSION_INTERVAL_UNAVAILABLE"})
            continue
        start, end = interval
        overlap = any(start <= old_end and end >= old_start for old_start, old_end in intervals)
        if overlap:
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

    parser = argparse.ArgumentParser(description="Audita BROOKS_FAILED_BREAKOUT_V1 por EXACT_CANDLE.")
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
