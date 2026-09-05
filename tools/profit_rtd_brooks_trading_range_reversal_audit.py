"""Auditoria EXACT_CANDLE para BROOKS_TRADING_RANGE_REVERSAL_V1.

Sequencia observacional:
    range valido em LOW/HIGH -> sinal de extremo -> reversao MODERATE/STRONG
    para dentro do range -> resposta explicita na mesma direcao

Nao reconstrói range a partir de retorno futuro. Pesquisa somente.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from research.price_action.brooks.trading_range_reversal import (
    BrooksTradingRangeReversalResearch,
    TradingRangeReversalObservation,
)

READY_STATUS = "CANDLE_EVIDENCE_READY"
MAX_SEQUENCE_WINDOW = 20


def _norm(value):
    return str(value or "").strip().upper()


def _direction(value):
    value = _norm(value)
    if value in {"UP", "BUY", "BULL", "BULLISH"}:
        return "BUY"
    if value in {"DOWN", "SELL", "BEAR", "BEARISH"}:
        return "SELL"
    return "NONE"


def _pa(row):
    value = row.get("price_action") or {}
    return value if isinstance(value, dict) else {}


def _candle_ts(row):
    raw = (row.get("candle_evidence") or {}).get("timestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _exact_identity_ready(payload):
    samples = payload.get("samples") or []
    return bool(samples) and all(
        (row.get("candle_evidence") or {}).get("status") == READY_STATUS
        and (row.get("candle_evidence") or {}).get("candle_id")
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


def _schema_ready(rows):
    required = {
        "brooks_trading_range_valid",
        "brooks_trading_range_zone",
        "brooks_trading_range_setup_direction",
        "brooks_trading_range_h2_near_low",
        "brooks_trading_range_l2_near_high",
        "brooks_trading_range_failed_breakout_risk",
        "brooks_trading_range_low",
        "brooks_trading_range_high",
    }
    return all(required.issubset(_pa(row)) for row in rows)


def _range_start(row):
    pa = _pa(row)
    if not bool(pa.get("brooks_trading_range_valid")):
        return None
    zone = _norm(pa.get("brooks_trading_range_zone"))
    if zone not in {"LOW", "HIGH"}:
        return None
    expected = "BUY" if zone == "LOW" else "SELL"
    edge_signal = bool(pa.get("brooks_trading_range_h2_near_low")) if expected == "BUY" else bool(pa.get("brooks_trading_range_l2_near_high"))
    if not (edge_signal or bool(pa.get("brooks_trading_range_failed_breakout_risk"))):
        return None
    setup_direction = _direction(pa.get("brooks_trading_range_setup_direction"))
    if setup_direction not in {"NONE", expected}:
        return None
    return zone, expected


def _reversal(row, expected):
    pa = _pa(row)
    return (
        bool(pa.get("brooks_reversal_candidate"))
        and _direction(pa.get("brooks_reversal_direction")) == expected
        and _norm(pa.get("brooks_reversal_quality")) in {"MODERATE", "STRONG"}
    )


def _response(row, expected):
    pa = _pa(row)
    return (
        _norm(pa.get("brooks_signal_phase")) in {"ENTRY_TRIGGERED", "FOLLOW_THROUGH"}
        and _direction(pa.get("brooks_signal_direction")) == expected
        and (bool(pa.get("brooks_entry_triggered")) or bool(pa.get("brooks_follow_through")))
    )


def _range_invalidated(row, zone):
    pa = _pa(row)
    if not bool(pa.get("brooks_trading_range_valid")):
        return True
    current_zone = _norm(pa.get("brooks_trading_range_zone"))
    if current_zone == "MIDDLE":
        return False
    # Opposite edge is not invalidation; it is normal two-sided range behavior.
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
    if not _schema_ready(rows):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["TRADING_RANGE_EVIDENCE_REQUIRED"], "sequences": [], **safety}

    research = BrooksTradingRangeReversalResearch()
    sequences = []

    for start_idx, start_row in enumerate(rows):
        start = _range_start(start_row)
        if not start:
            continue
        zone, expected = start
        end_idx = min(len(rows), start_idx + 1 + int(max_sequence_window))

        reversal_idx = None
        invalidated = False
        for idx in range(start_idx, end_idx):
            row = rows[idx]
            if idx > start_idx and _range_invalidated(row, zone):
                invalidated = True
                break
            if _reversal(row, expected):
                reversal_idx = idx
                break

        if reversal_idx is None:
            sequences.append({
                "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
                "zone": zone,
                "direction": expected,
                "matched": False,
                "invalidated": invalidated,
                "reason": "TRADING_RANGE_INVALIDATED_BEFORE_REVERSAL" if invalidated else "REVERSAL_NOT_OBSERVED",
            })
            continue

        response_detected = False
        response_candle_id = None
        invalidated_after_reversal = False
        for idx in range(reversal_idx + 1, end_idx):
            row = rows[idx]
            if _range_invalidated(row, zone):
                invalidated_after_reversal = True
                break
            if _response(row, expected):
                response_detected = True
                response_candle_id = (row.get("candle_evidence") or {}).get("candle_id")
                break

        start_pa = _pa(start_row)
        reversal_row = rows[reversal_idx]
        reversal_pa = _pa(reversal_row)
        obs = TradingRangeReversalObservation(
            range_valid=True,
            zone=zone,
            setup_direction=start_pa.get("brooks_trading_range_setup_direction", "NONE"),
            h2_near_low=bool(start_pa.get("brooks_trading_range_h2_near_low")),
            l2_near_high=bool(start_pa.get("brooks_trading_range_l2_near_high")),
            failed_breakout_risk=bool(start_pa.get("brooks_trading_range_failed_breakout_risk")),
            reversal_candidate=True,
            reversal_direction=expected,
            reversal_quality=reversal_pa.get("brooks_reversal_quality", "NONE"),
            response_detected=response_detected,
            range_invalidated=invalidated_after_reversal,
            candle_id=(reversal_row.get("candle_evidence") or {}).get("candle_id"),
        )
        result = research.evaluate(obs)
        sequences.append({
            "start_candle_id": (start_row.get("candle_evidence") or {}).get("candle_id"),
            "reversal_candle_id": (reversal_row.get("candle_evidence") or {}).get("candle_id"),
            "response_candle_id": response_candle_id,
            "range_low": start_pa.get("brooks_trading_range_low"),
            "range_high": start_pa.get("brooks_trading_range_high"),
            "zone": zone,
            **asdict(result),
        })

    return {
        "status": "AUDIT_COMPLETED",
        "deduplication": "EXACT_CANDLE_LAST_REVISION",
        "exact_candle_identity_available": True,
        "sequence_count": len(sequences),
        "matched_sequence_count": sum(1 for x in sequences if x.get("matched")),
        "sequences": sequences,
        **safety,
    }


def _session_interval(payload):
    rows = _last_revision_rows(payload)
    ts = [x for x in (_candle_ts(row) for row in rows) if x is not None]
    return (min(ts), max(ts)) if ts else None


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
        audit = audit_payload(payload, max_sequence_window=max_sequence_window)
        if audit.get("status") != "AUDIT_COMPLETED":
            rejected.append({"session_index": index, "reason": "SESSION_NOT_ELIGIBLE", "audit": audit})
            continue
        intervals.append(interval)
        accepted.append({"session_index": index, "audit": audit})
    return {
        "status": "MULTI_SESSION_AUDIT_COMPLETED",
        "accepted_session_count": len(accepted),
        "rejected_session_count": len(rejected),
        "accepted_sessions": accepted,
        "rejected_sessions": rejected,
        "matched_sequence_count": sum(x["audit"].get("matched_sequence_count", 0) for x in accepted),
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
    parser = argparse.ArgumentParser(description="Audita BROOKS_TRADING_RANGE_REVERSAL_V1 por EXACT_CANDLE.")
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
