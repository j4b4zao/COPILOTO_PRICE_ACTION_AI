"""Auditoria EXACT_CANDLE observacional para BROOKS_STOP_TARGET_RULES_V1.

Somente registros prospectivos com candle-sinal identificado, stop valido e
alvo estrutural capturado podem ter desfecho avaliado. O candle de entrada nao
e usado para decidir ordem intrabar. Nenhum alvo e reconstruido ou sintetizado.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


READY_STATUS = "CANDLE_EVIDENCE_READY"
MAX_OUTCOME_WINDOW = 20


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
        "hypothesis_freeze_allowed": False,
    }


def _pa(row):
    value = row.get("price_action") or {}
    return value if isinstance(value, dict) else {}


def _candle(row):
    value = row.get("candle_evidence") or {}
    return value if isinstance(value, dict) else {}


def _timestamp(row):
    raw = _candle(row).get("timestamp")
    try:
        return datetime.fromisoformat(str(raw)) if raw else None
    except ValueError:
        return None


def _last_revision_rows(payload):
    latest = {}
    order = []
    for row in payload.get("samples") or []:
        candle = _candle(row)
        candle_id = candle.get("candle_id")
        if candle.get("status") != READY_STATUS or not candle_id:
            continue
        if candle_id not in latest:
            order.append(candle_id)
        latest[candle_id] = row
    rows = [latest[candle_id] for candle_id in order]
    rows.sort(key=lambda row: (_timestamp(row) or datetime.min, str(_candle(row).get("candle_id"))))
    return rows


def _exact_identity_ready(payload):
    samples = payload.get("samples") or []
    return bool(samples) and all(
        _candle(row).get("status") == READY_STATUS and _candle(row).get("candle_id")
        for row in samples
    )


def _schema_ready(rows):
    required = {
        "brooks_stop_target_capture_status",
        "brooks_stop_target_direction",
        "brooks_stop_target_entry_triggered",
        "brooks_stop_target_entry_price",
        "brooks_stop_target_initial_stop",
        "brooks_stop_target_stop_geometry_valid",
        "brooks_stop_target_target_price",
        "brooks_stop_target_target_valid",
        "brooks_stop_target_target_source",
        "brooks_stop_target_candle_id",
    }
    return bool(rows) and all(required.issubset(_pa(row)) for row in rows)


def _prospective_observation(row):
    pa = _pa(row)
    candle_id = _candle(row).get("candle_id")
    return (
        pa.get("brooks_stop_target_capture_status") == "ELIGIBLE"
        and bool(pa.get("brooks_stop_target_entry_triggered"))
        and bool(pa.get("brooks_stop_target_stop_geometry_valid"))
        and pa.get("brooks_stop_target_candle_id") == candle_id
        and pa.get("brooks_stop_target_direction") in {"BUY", "SELL"}
    )


def _price(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hits(row, *, direction, stop, target):
    candle = _candle(row)
    high = _price(candle.get("high"))
    low = _price(candle.get("low"))
    if high is None or low is None:
        return False, False
    if direction == "BUY":
        return low <= stop, high >= target
    return high >= stop, low <= target


def audit_payload(payload, *, max_outcome_window=MAX_OUTCOME_WINDOW):
    safety = _safety()
    if not bool(payload.get("data_ready")):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["DATA_NOT_READY"], "observations": [], **safety}
    if not _exact_identity_ready(payload):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["EXACT_CANDLE_IDENTITY_REQUIRED"], "observations": [], **safety}

    rows = _last_revision_rows(payload)
    if not _schema_ready(rows):
        return {"status": "SESSION_NOT_ELIGIBLE", "reasons": ["STOP_TARGET_EVIDENCE_REQUIRED"], "observations": [], **safety}

    prospective = [(index, row) for index, row in enumerate(rows) if _prospective_observation(row)]
    if not prospective:
        return {
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["NO_PROSPECTIVE_STOP_TARGET_EVIDENCE"],
            "observations": [],
            **safety,
        }

    observations = []
    for start_index, row in prospective:
        pa = _pa(row)
        direction = pa["brooks_stop_target_direction"]
        entry = _price(pa.get("brooks_stop_target_entry_price"))
        stop = _price(pa.get("brooks_stop_target_initial_stop"))
        target = _price(pa.get("brooks_stop_target_target_price"))
        target_valid = bool(pa.get("brooks_stop_target_target_valid"))
        base = {
            "entry_candle_id": _candle(row).get("candle_id"),
            "direction": direction,
            "entry_price": entry,
            "initial_stop": stop,
            "target_price": target,
            "target_source": pa.get("brooks_stop_target_target_source"),
        }
        if not target_valid or target is None:
            observations.append({
                **base,
                "evaluable": False,
                "outcome": "NOT_EVALUABLE",
                "reason": "STRUCTURAL_TARGET_NOT_AVAILABLE",
                "outcome_candle_id": None,
            })
            continue

        outcome = "UNRESOLVED_IN_WINDOW"
        reason = "NO_STOP_OR_TARGET_HIT_IN_WINDOW"
        outcome_candle_id = None
        end = min(len(rows), start_index + 1 + int(max_outcome_window))
        for future in rows[start_index + 1:end]:
            stop_hit, target_hit = _hits(future, direction=direction, stop=stop, target=target)
            if stop_hit and target_hit:
                outcome = "AMBIGUOUS_SAME_CANDLE"
                reason = "INTRABAR_ORDER_UNAVAILABLE"
            elif stop_hit:
                outcome = "STOP_FIRST"
                reason = "OBSERVED_STOP_HIT"
            elif target_hit:
                outcome = "TARGET_FIRST"
                reason = "OBSERVED_TARGET_HIT"
            else:
                continue
            outcome_candle_id = _candle(future).get("candle_id")
            break
        observations.append({
            **base,
            "evaluable": True,
            "outcome": outcome,
            "reason": reason,
            "outcome_candle_id": outcome_candle_id,
        })

    evaluable = [item for item in observations if item["evaluable"]]
    resolved = [item for item in evaluable if item["outcome"] in {"STOP_FIRST", "TARGET_FIRST"}]
    return {
        "status": "AUDIT_COMPLETED",
        "deduplication": "EXACT_CANDLE_LAST_REVISION",
        "entry_candle_outcome_policy": "SUBSEQUENT_CANDLES_ONLY",
        "exact_candle_identity_available": True,
        "observation_count": len(observations),
        "evaluable_observation_count": len(evaluable),
        "resolved_observation_count": len(resolved),
        "target_first_count": sum(item["outcome"] == "TARGET_FIRST" for item in evaluable),
        "stop_first_count": sum(item["outcome"] == "STOP_FIRST" for item in evaluable),
        "ambiguous_same_candle_count": sum(item["outcome"] == "AMBIGUOUS_SAME_CANDLE" for item in evaluable),
        "unresolved_in_window_count": sum(item["outcome"] == "UNRESOLVED_IN_WINDOW" for item in evaluable),
        "sequence_count": len(evaluable),
        "matched_sequence_count": len(resolved),
        "observations": observations,
        **safety,
    }


def audit_sessions(payloads, *, max_outcome_window=MAX_OUTCOME_WINDOW):
    accepted, rejected, intervals = [], [], []
    for index, payload in enumerate(payloads):
        rows = _last_revision_rows(payload)
        timestamps = [value for value in (_timestamp(row) for row in rows) if value is not None]
        if not timestamps:
            rejected.append({"session_index": index, "reason": "SESSION_INTERVAL_UNAVAILABLE"})
            continue
        interval = min(timestamps), max(timestamps)
        if any(interval[0] <= old[1] and interval[1] >= old[0] for old in intervals):
            rejected.append({"session_index": index, "reason": "TEMPORAL_OVERLAP"})
            continue
        result = audit_payload(payload, max_outcome_window=max_outcome_window)
        if result.get("status") != "AUDIT_COMPLETED":
            rejected.append({"session_index": index, "reason": "SESSION_NOT_ELIGIBLE", "audit": result})
            continue
        intervals.append(interval)
        accepted.append({"session_index": index, "audit": result})

    audits = [item["audit"] for item in accepted]
    return {
        "status": "MULTI_SESSION_AUDIT_COMPLETED",
        "accepted_session_count": len(accepted),
        "rejected_session_count": len(rejected),
        "accepted_sessions": accepted,
        "rejected_sessions": rejected,
        "observation_count": sum(item.get("observation_count", 0) for item in audits),
        "evaluable_observation_count": sum(item.get("evaluable_observation_count", 0) for item in audits),
        "resolved_observation_count": sum(item.get("resolved_observation_count", 0) for item in audits),
        "sequence_count": sum(item.get("sequence_count", 0) for item in audits),
        "matched_sequence_count": sum(item.get("matched_sequence_count", 0) for item in audits),
        **_safety(),
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Audita BROOKS_STOP_TARGET_RULES_V1 por EXACT_CANDLE.")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    parser.add_argument("--max-outcome-window", type=int, default=MAX_OUTCOME_WINDOW)
    args = parser.parse_args(argv)
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.paths]
    result = (
        audit_sessions(payloads, max_outcome_window=args.max_outcome_window)
        if len(payloads) > 1
        else audit_payload(payloads[0], max_outcome_window=args.max_outcome_window)
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
