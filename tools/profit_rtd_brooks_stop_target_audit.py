"""Auditoria EXACT_CANDLE de BROOKS_STOP_TARGET_RULES_V1.

Pesquisa apenas. Nao altera Score/Risk/Decision/Alert/execucao.

O auditor valida somente evidencia explicitamente capturada no JSON:
- identidade exata do candle e ultima revisao por candle;
- direcao, entrada e geometria do stop inicial;
- alvo estrutural capturado, sua origem e geometria;
- reward/risk capturado e consistencia aritmetica.

Nao infere trailing stop, stop loosened, parcial, alvo atingido ou pressao de
realizacao porque esses eventos dinamicos ainda nao fazem parte do contrato de
captura Brooks Stop/Target.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from tools.profit_rtd_price_action_evidence_audit import _session_interval

SETUP_NAME = "BROOKS_STOP_TARGET_RULES_V1"

_REQUIRED_FIELDS = {
    "brooks_stop_target_capture_status",
    "brooks_stop_target_direction",
    "brooks_stop_target_entry_triggered",
    "brooks_stop_target_entry_price",
    "brooks_stop_target_initial_stop",
    "brooks_stop_target_stop_geometry_valid",
    "brooks_stop_target_target_price",
    "brooks_stop_target_target_valid",
    "brooks_stop_target_target_source",
    "brooks_stop_target_reward_risk",
    "brooks_stop_target_candle_id",
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
        "hypothesis_freeze_allowed": False,
    }


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


def _dedup(rows):
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


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _valid_stop_geometry(direction, entry, stop):
    if direction == "BUY":
        return 0 < stop < entry
    if direction == "SELL":
        return stop > entry > 0
    return False


def _valid_target_geometry(direction, entry, target):
    if direction == "BUY":
        return target > entry > 0
    if direction == "SELL":
        return 0 < target < entry
    return False


def _row_has_contract(row):
    pa = row.get("price_action") or {}
    return isinstance(pa, dict) and _REQUIRED_FIELDS.issubset(pa.keys())


def _audit_row(row):
    pa = row.get("price_action") or {}
    candle_id = row["candle_evidence"]["candle_id"]

    reasons = []
    mismatches = []

    captured_candle_id = pa.get("brooks_stop_target_candle_id")
    if captured_candle_id != candle_id:
        mismatches.append("CAPTURE_CANDLE_ID_MISMATCH")

    direction = _text(pa.get("brooks_stop_target_direction"))
    triggered = pa.get("brooks_stop_target_entry_triggered") is True
    entry = _number(pa.get("brooks_stop_target_entry_price"))
    stop = _number(pa.get("brooks_stop_target_initial_stop"))
    target = _number(pa.get("brooks_stop_target_target_price"))
    captured_stop_valid = pa.get("brooks_stop_target_stop_geometry_valid") is True
    captured_target_valid = pa.get("brooks_stop_target_target_valid") is True
    captured_status = _text(pa.get("brooks_stop_target_capture_status"))
    target_source = _text(pa.get("brooks_stop_target_target_source"))
    captured_rr = _number(pa.get("brooks_stop_target_reward_risk"))

    numeric_ready = entry is not None and stop is not None and target is not None and captured_rr is not None
    if not numeric_ready:
        mismatches.append("NON_NUMERIC_CAPTURE_VALUE")
        entry = entry or 0.0
        stop = stop or 0.0
        target = target or 0.0
        captured_rr = captured_rr or 0.0

    computed_stop_valid = triggered and _valid_stop_geometry(direction, entry, stop)
    if captured_stop_valid != computed_stop_valid:
        mismatches.append("STOP_GEOMETRY_FLAG_MISMATCH")

    expected_status = "ELIGIBLE" if computed_stop_valid else "NOT_ELIGIBLE"
    if captured_status != expected_status:
        mismatches.append("CAPTURE_STATUS_MISMATCH")

    computed_target_valid = (
        triggered
        and computed_stop_valid
        and _valid_target_geometry(direction, entry, target)
    )
    if captured_target_valid != computed_target_valid:
        mismatches.append("TARGET_GEOMETRY_FLAG_MISMATCH")

    if captured_target_valid and target_source == "NONE":
        mismatches.append("TARGET_SOURCE_REQUIRED")
    if not captured_target_valid and target_source != "NONE":
        mismatches.append("TARGET_SOURCE_WITHOUT_VALID_TARGET")

    risk = abs(entry - stop) if computed_stop_valid else 0.0
    reward = abs(target - entry) if computed_target_valid else 0.0
    computed_rr = reward / risk if risk > 0 and computed_target_valid else 0.0
    if not math.isclose(captured_rr, computed_rr, rel_tol=1e-9, abs_tol=1e-9):
        mismatches.append("REWARD_RISK_MISMATCH")

    if triggered:
        reasons.append("ENTRY_TRIGGER_CAPTURED")
    if computed_stop_valid:
        reasons.append("PROTECTIVE_STOP_GEOMETRY_EXACT")
    if computed_target_valid:
        reasons.append("STRUCTURAL_TARGET_GEOMETRY_EXACT")
        reasons.append("REWARD_RISK_EXACT")

    return {
        "candle_id": candle_id,
        "direction": direction,
        "entry_triggered": triggered,
        "entry_price": entry,
        "initial_stop": stop,
        "stop_geometry_valid": computed_stop_valid,
        "target_price": target,
        "target_valid": computed_target_valid,
        "target_source": target_source,
        "reward_risk": captured_rr,
        "computed_reward_risk": computed_rr,
        "capture_consistent": not mismatches,
        "mismatches": mismatches,
        "reasons": reasons,
    }


def audit_payload(payload):
    raw = _rows(payload)
    if not isinstance(payload, dict) or payload.get("data_ready") is not True:
        return {
            "setup": SETUP_NAME,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["DATA_NOT_READY"],
            **_safety(),
        }
    if not raw:
        return {
            "setup": SETUP_NAME,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["SAMPLES_REQUIRED"],
            **_safety(),
        }
    if not all(_exact_ready(row) for row in raw):
        return {
            "setup": SETUP_NAME,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["EXACT_CANDLE_IDENTITY_REQUIRED"],
            **_safety(),
        }

    rows = _dedup(raw)
    coverage = sum(_row_has_contract(row) for row in rows)
    if coverage != len(rows):
        return {
            "setup": SETUP_NAME,
            "status": "SESSION_NOT_ELIGIBLE",
            "exact_candles": len(rows),
            "stop_target_evidence_rows": coverage,
            "missing_stop_target_evidence_rows": len(rows) - coverage,
            "deduplication": "EXACT_CANDLE_LAST_REVISION",
            "reasons": ["STOP_TARGET_CAPTURE_CONTRACT_REQUIRED"],
            **_safety(),
        }

    observations = [_audit_row(row) for row in rows]
    inconsistent = [item for item in observations if not item["capture_consistent"]]
    eligible = [item for item in observations if item["stop_geometry_valid"]]
    target_valid = [item for item in eligible if item["target_valid"]]

    return {
        "setup": SETUP_NAME,
        "status": "EXACT_AUDIT_COMPLETED" if not inconsistent else "CAPTURE_INCONSISTENCY_OBSERVED",
        "exact_candles": len(rows),
        "stop_target_evidence_rows": coverage,
        "eligible_stop_observations": len(eligible),
        "valid_target_observations": len(target_valid),
        "capture_inconsistency_count": len(inconsistent),
        "deduplication": "EXACT_CANDLE_LAST_REVISION",
        "dynamic_management_audited": False,
        "dynamic_management_reason": "TRAILING_PARTIAL_AND_OUTCOME_FIELDS_NOT_CAPTURED",
        "observations": observations,
        "reasons": [] if not inconsistent else ["STOP_TARGET_CAPTURE_INCONSISTENCY_OBSERVED"],
        **_safety(),
    }


def audit_sessions(payloads):
    candidates = []
    for index, payload in enumerate(payloads):
        interval = _session_interval(_rows(payload))
        candidates.append((index, payload, interval))
    candidates.sort(key=lambda item: (
        item[2] is None,
        item[2][0] if item[2] else float("inf"),
        item[0],
    ))

    accepted_intervals = []
    sessions = []
    rejected_sessions = []
    for index, payload, interval in candidates:
        overlap = next((
            prior_index
            for prior_index, prior_interval in accepted_intervals
            if interval
            and interval[0] <= prior_interval[1]
            and prior_interval[0] <= interval[1]
        ), None)
        if overlap is not None:
            rejected_sessions.append({
                "session_index": index,
                "reason": "TEMPORAL_OVERLAP",
                "overlaps_with_session_index": overlap,
            })
            continue

        result = audit_payload(payload)
        result["session_index"] = index
        sessions.append(result)
        if interval and result.get("status") in {"EXACT_AUDIT_COMPLETED", "CAPTURE_INCONSISTENCY_OBSERVED"}:
            accepted_intervals.append((index, interval))

    total_exact = sum(item.get("exact_candles", 0) for item in sessions)
    total_eligible = sum(item.get("eligible_stop_observations", 0) for item in sessions)
    total_targets = sum(item.get("valid_target_observations", 0) for item in sessions)
    total_inconsistent = sum(item.get("capture_inconsistency_count", 0) for item in sessions)

    return {
        "setup": SETUP_NAME,
        "status": "MULTI_SESSION_EXACT_AUDIT_COMPLETED" if not total_inconsistent else "CAPTURE_INCONSISTENCY_OBSERVED",
        "accepted_session_count": len(sessions),
        "rejected_session_count": len(rejected_sessions),
        "exact_candles": total_exact,
        "eligible_stop_observations": total_eligible,
        "valid_target_observations": total_targets,
        "capture_inconsistency_count": total_inconsistent,
        "deduplication": "EXACT_CANDLE_LAST_REVISION",
        "dynamic_management_audited": False,
        "dynamic_management_reason": "TRAILING_PARTIAL_AND_OUTCOME_FIELDS_NOT_CAPTURED",
        "sessions": sessions,
        "rejected_sessions": rejected_sessions,
        "reasons": [] if not total_inconsistent else ["STOP_TARGET_CAPTURE_INCONSISTENCY_OBSERVED"],
        **_safety(),
    }


def audit(paths):
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]
    if len(payloads) == 1:
        return audit_payload(payloads[0])
    return audit_sessions(payloads)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    result = audit(args.paths)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
