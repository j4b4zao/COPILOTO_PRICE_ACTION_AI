"""
tools/profit_rtd_brooks_trailing_stop_exact_audit.py

Auditoria exata da captura Brooks de trailing stop.

Contrato:
- deduplicacao por candle_id usando a ultima revisao observada;
- avalia somente campos persistidos;
- nao recalcula estrategia operacional;
- nao acessa RiskManager, Score, Decision, Alert ou execucao;
- classifica ADVANCE, HOLD e inconsistencias de captura;
- research-only.

Este auditor valida consistencia de captura, nao lucratividade nem valor preditivo.
"""

from __future__ import annotations

import json
from pathlib import Path


SETUP_NAME = "BROOKS_MANAGEMENT_RESEARCH_V1"
DEDUPLICATION = "EXACT_CANDLE_LAST_REVISION"

ADVANCE_STATES = {"TRAILING_STOP_ADVANCE"}
HOLD_STATES = {
    "TRAILING_STOP_HOLD",
    "PROTECTIVE_STOP_HOLD",
}
REJECT_STATES = {
    "STOP_LOOSENING_REJECTED",
    "INVALID_PROTECTIVE_STOP",
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


def _load_payload(path_or_payload):
    if isinstance(path_or_payload, dict):
        return path_or_payload

    path = Path(path_or_payload)
    return json.loads(path.read_text(encoding="utf-8"))


def _deduplicate(samples):
    by_candle = {}
    order = []

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        evidence = sample.get("candle_evidence") or {}
        candle_id = evidence.get("candle_id")
        if not candle_id:
            continue

        candle_id = str(candle_id)
        if candle_id not in by_candle:
            order.append(candle_id)

        by_candle[candle_id] = sample

    return [by_candle[candle_id] for candle_id in order]


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _audit_sample(sample):
    evidence = sample.get("candle_evidence") or {}
    pa = sample.get("price_action") or {}

    candle_id = str(evidence.get("candle_id") or "")
    status = str(pa.get("brooks_management_capture_status") or "")
    state = str(pa.get("brooks_management_state") or "")
    direction = str(pa.get("brooks_management_direction") or "").upper()

    initial_stop = _float(pa.get("brooks_management_initial_stop"))
    current_stop = _float(pa.get("brooks_management_current_stop"))
    proposed_stop = _float(pa.get("brooks_management_proposed_stop"))

    trailing_active = bool(pa.get("brooks_management_trailing_active"))
    improved = bool(pa.get("brooks_management_stop_improved"))
    loosened = bool(pa.get("brooks_management_stop_loosened"))
    structural = bool(
        pa.get("brooks_management_structural_advance_confirmed")
    )

    inconsistencies = []

    if status not in {"CAPTURED", "REJECTED", "NOT_ELIGIBLE"}:
        inconsistencies.append("INVALID_CAPTURE_STATUS")

    if status == "CAPTURED":
        if direction not in {"BUY", "SELL"}:
            inconsistencies.append("INVALID_DIRECTION")

        if initial_stop <= 0 or current_stop <= 0 or proposed_stop <= 0:
            inconsistencies.append("INVALID_STOP_PRICE")

        if current_stop != initial_stop:
            inconsistencies.append("CURRENT_STOP_NOT_EQUAL_INITIAL_STOP_V1")

        if state in ADVANCE_STATES:
            if not trailing_active:
                inconsistencies.append("ADVANCE_WITHOUT_TRAILING_ACTIVE")
            if not structural:
                inconsistencies.append("ADVANCE_WITHOUT_STRUCTURAL_CONFIRMATION")
            if not improved:
                inconsistencies.append("ADVANCE_WITHOUT_STOP_IMPROVEMENT")

            if direction == "BUY" and not (proposed_stop > current_stop):
                inconsistencies.append("BUY_ADVANCE_NOT_TIGHTER")
            if direction == "SELL" and not (proposed_stop < current_stop):
                inconsistencies.append("SELL_ADVANCE_NOT_TIGHTER")

        elif state in HOLD_STATES:
            if improved:
                inconsistencies.append("HOLD_WITH_STOP_IMPROVEMENT")

            if proposed_stop != current_stop:
                inconsistencies.append("HOLD_CHANGED_STOP")

        elif state in REJECT_STATES:
            pass
        else:
            inconsistencies.append("UNKNOWN_MANAGEMENT_STATE")

        if loosened and state != "STOP_LOOSENING_REJECTED":
            inconsistencies.append("LOOSENING_NOT_REJECTED")

    return {
        "candle_id": candle_id,
        "capture_status": status,
        "state": state,
        "direction": direction,
        "initial_stop": initial_stop,
        "current_stop": current_stop,
        "proposed_stop": proposed_stop,
        "trailing_active": trailing_active,
        "stop_improved": improved,
        "stop_loosened": loosened,
        "structural_advance_confirmed": structural,
        "consistent": not inconsistencies,
        "inconsistencies": inconsistencies,
    }


def audit_session(path_or_payload):
    payload = _load_payload(path_or_payload)
    samples = payload.get("samples") or []
    exact_samples = _deduplicate(samples)

    audited = [_audit_sample(sample) for sample in exact_samples]

    captured = [
        row for row in audited
        if row["capture_status"] == "CAPTURED"
    ]
    eligible = [
        row for row in audited
        if row["capture_status"] in {"CAPTURED", "REJECTED"}
    ]
    advances = [
        row for row in captured
        if row["state"] == "TRAILING_STOP_ADVANCE"
    ]
    holds = [
        row for row in captured
        if row["state"] in HOLD_STATES
    ]
    rejected = [
        row for row in audited
        if row["capture_status"] == "REJECTED"
        or row["state"] in REJECT_STATES
    ]
    inconsistencies = [
        row for row in audited
        if not row["consistent"]
    ]

    if inconsistencies:
        status = "CAPTURE_INCONSISTENCY_DETECTED"
    elif not eligible:
        status = "MORE_EVIDENCE_REQUIRED"
    else:
        status = "EXACT_AUDIT_COMPLETED"

    return {
        "setup": SETUP_NAME,
        "status": status,
        "deduplication": DEDUPLICATION,
        "raw_samples": len(samples),
        "exact_candles": len(exact_samples),
        "eligible_trailing_observations": len(eligible),
        "captured_trailing_observations": len(captured),
        "trailing_advance_observations": len(advances),
        "trailing_hold_observations": len(holds),
        "trailing_rejected_observations": len(rejected),
        "capture_inconsistency_count": len(inconsistencies),
        "hypothesis_freeze_allowed": False,
        "dynamic_management_validated": False,
        "validation_reason": (
            "CAPTURE_CONSISTENCY_ONLY_NO_PERFORMANCE_CLAIM"
        ),
        "observations": audited,
        **_safety(),
    }


def audit_many(paths):
    reports = [audit_session(path) for path in paths]

    totals = {
        "raw_samples": 0,
        "exact_candles": 0,
        "eligible_trailing_observations": 0,
        "captured_trailing_observations": 0,
        "trailing_advance_observations": 0,
        "trailing_hold_observations": 0,
        "trailing_rejected_observations": 0,
        "capture_inconsistency_count": 0,
    }

    for report in reports:
        for key in totals:
            totals[key] += int(report.get(key, 0))

    if totals["capture_inconsistency_count"] > 0:
        status = "MULTI_SESSION_CAPTURE_INCONSISTENCY_DETECTED"
    elif totals["eligible_trailing_observations"] == 0:
        status = "MORE_EVIDENCE_REQUIRED"
    else:
        status = "MULTI_SESSION_EXACT_AUDIT_COMPLETED"

    return {
        "setup": SETUP_NAME,
        "status": status,
        "accepted_session_count": len(reports),
        "deduplication": DEDUPLICATION,
        **totals,
        "hypothesis_freeze_allowed": False,
        "dynamic_management_validated": False,
        "validation_reason": (
            "CAPTURE_CONSISTENCY_ONLY_NO_PERFORMANCE_CLAIM"
        ),
        "sessions": reports,
        **_safety(),
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Auditoria exata Brooks trailing stop."
    )
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = audit_many(args.paths)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("status=", report["status"])
    print("accepted_session_count=", report["accepted_session_count"])
    print("exact_candles=", report["exact_candles"])
    print(
        "eligible_trailing_observations=",
        report["eligible_trailing_observations"],
    )
    print(
        "trailing_advance_observations=",
        report["trailing_advance_observations"],
    )
    print(
        "trailing_hold_observations=",
        report["trailing_hold_observations"],
    )
    print(
        "capture_inconsistency_count=",
        report["capture_inconsistency_count"],
    )

    return 0 if report["capture_inconsistency_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
