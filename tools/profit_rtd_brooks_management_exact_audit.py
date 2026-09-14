"""Auditor EXACT_CANDLE research-only para Brooks Management / Trailing Stop."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

SETUP = "BROOKS_MANAGEMENT_RESEARCH_V1"
COMPONENT = "TRAILING_STOP_V1"
READY_STATUS = "CANDLE_EVIDENCE_READY"
DEDUPLICATION = "EXACT_CANDLE_LAST_REVISION"


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


def _pa(sample):
    value = sample.get("price_action") if isinstance(sample, dict) else None
    return value if isinstance(value, dict) else {}


def _evidence(sample):
    value = sample.get("candle_evidence") if isinstance(sample, dict) else None
    return value if isinstance(value, dict) else {}


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _ready_candle(sample):
    ev = _evidence(sample)
    return (
        ev.get("status") == READY_STATUS
        and bool(ev.get("identity_ready", True))
        and bool(ev.get("candle_id"))
    )


def _dedupe_exact_candles(samples):
    order = []
    latest = {}
    for sample in samples:
        if not _ready_candle(sample):
            continue
        cid = _evidence(sample).get("candle_id")
        if cid not in latest:
            order.append(cid)
        latest[cid] = sample
    return [latest[cid] for cid in order]


def _management_contract_present(pa):
    return (
        pa.get("brooks_management_component") == COMPONENT
        and "brooks_management_capture_status" in pa
    )


def _check_observation(sample):
    pa = _pa(sample)
    ev = _evidence(sample)
    cid = ev.get("candle_id")

    direction = str(pa.get("brooks_management_direction") or "NONE").upper()
    capture_status = str(pa.get("brooks_management_capture_status") or "UNKNOWN")
    state = str(pa.get("brooks_management_state") or "UNKNOWN")

    entry = _float(pa.get("brooks_management_entry_price"))
    initial = _float(pa.get("brooks_management_initial_stop"))
    current = _float(pa.get("brooks_management_current_stop"))
    proposed = _float(pa.get("brooks_management_proposed_stop"))

    improved = bool(pa.get("brooks_management_stop_improved"))
    loosened_flag = bool(pa.get("brooks_management_stop_loosened"))
    structural = bool(pa.get("brooks_management_structural_advance_confirmed"))

    mismatches = []

    if pa.get("brooks_management_component") != COMPONENT:
        mismatches.append("MANAGEMENT_COMPONENT_MISMATCH")

    if pa.get("brooks_management_research_only") is not True:
        mismatches.append("MANAGEMENT_RESEARCH_ONLY_REQUIRED")
    if pa.get("brooks_management_observational_only") is not True:
        mismatches.append("MANAGEMENT_OBSERVATIONAL_ONLY_REQUIRED")

    for field in (
        "brooks_management_predictive_claim_allowed",
        "brooks_management_score_influence_allowed",
        "brooks_management_risk_influence_allowed",
        "brooks_management_decision_influence_allowed",
        "brooks_management_alert_influence_allowed",
        "brooks_management_order_execution_allowed",
    ):
        if pa.get(field) is not False:
            mismatches.append(field.upper() + "_MUST_BE_FALSE")

    st_cid = pa.get("brooks_stop_target_candle_id")
    if st_cid and st_cid != cid:
        mismatches.append("STOP_TARGET_CANDLE_ID_MISMATCH")

    st_direction = str(pa.get("brooks_stop_target_direction") or "NONE").upper()
    if st_direction in {"BUY", "SELL"} and direction != st_direction:
        mismatches.append("MANAGEMENT_DIRECTION_MISMATCH")

    if bool(pa.get("brooks_stop_target_entry_triggered")) != bool(
        pa.get("brooks_management_entry_triggered")
    ):
        mismatches.append("ENTRY_TRIGGER_MISMATCH")

    st_entry = _float(pa.get("brooks_stop_target_entry_price"))
    st_initial = _float(pa.get("brooks_stop_target_initial_stop"))
    if st_entry and entry and st_entry != entry:
        mismatches.append("ENTRY_PRICE_MISMATCH")
    if st_initial and initial and st_initial != initial:
        mismatches.append("INITIAL_STOP_MISMATCH")

    geometry_loosened = False
    geometry_improved = False
    if direction == "BUY" and current and proposed:
        geometry_loosened = proposed < current
        geometry_improved = proposed > current
    elif direction == "SELL" and current and proposed:
        geometry_loosened = proposed > current
        geometry_improved = proposed < current

    if loosened_flag:
        mismatches.append("STOP_LOOSENED_FLAG_TRUE")
    if geometry_loosened:
        mismatches.append("STOP_GEOMETRY_LOOSENED")
    if improved != geometry_improved:
        mismatches.append("STOP_IMPROVEMENT_FLAG_MISMATCH")

    if capture_status == "CAPTURED":
        if direction not in {"BUY", "SELL"}:
            mismatches.append("CAPTURED_DIRECTION_REQUIRED")
        if not initial or not current or not proposed:
            mismatches.append("CAPTURED_STOP_VALUES_REQUIRED")

    reasons = []
    if not mismatches:
        reasons.append("EXACT_CANDLE_MANAGEMENT_CAPTURE_CONSISTENT")
    if capture_status == "CAPTURED":
        reasons.append("MANAGEMENT_CAPTURED")
    if improved:
        reasons.append("STOP_IMPROVEMENT_OBSERVED")
    if structural:
        reasons.append("STRUCTURAL_ADVANCE_OBSERVED")
    if not loosened_flag and not geometry_loosened:
        reasons.append("NO_STOP_LOOSENING")

    return {
        "candle_id": cid,
        "capture_status": capture_status,
        "state": state,
        "direction": direction,
        "entry_triggered": bool(pa.get("brooks_management_entry_triggered")),
        "entry_price": entry,
        "initial_stop": initial,
        "current_stop": current,
        "proposed_stop": proposed,
        "trailing_active": bool(pa.get("brooks_management_trailing_active")),
        "stop_improved": improved,
        "stop_loosened": loosened_flag,
        "structural_advance_confirmed": structural,
        "latest_swing_index": pa.get("brooks_management_latest_swing_index"),
        "latest_swing_price": _float(pa.get("brooks_management_latest_swing_price")),
        "protected_r": _float(pa.get("brooks_management_protected_r")),
        "capture_consistent": not mismatches,
        "mismatches": mismatches,
        "reasons": reasons,
    }


def audit_payload(payload):
    samples = payload.get("samples") if isinstance(payload, dict) else None
    samples = samples if isinstance(samples, list) else []

    exact = _dedupe_exact_candles(samples)
    rows = [s for s in exact if _management_contract_present(_pa(s))]

    if not bool(payload.get("data_ready")):
        return {
            "setup": SETUP,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["DATA_NOT_READY"],
            "exact_candles": len(exact),
            "management_evidence_rows": len(rows),
            "hypothesis_freeze_allowed": False,
            **_safety(),
        }

    if not exact:
        return {
            "setup": SETUP,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["EXACT_CANDLE_EVIDENCE_REQUIRED"],
            "exact_candles": 0,
            "management_evidence_rows": 0,
            "hypothesis_freeze_allowed": False,
            **_safety(),
        }

    if not rows:
        return {
            "setup": SETUP,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["MANAGEMENT_CAPTURE_CONTRACT_REQUIRED"],
            "exact_candles": len(exact),
            "management_evidence_rows": 0,
            "hypothesis_freeze_allowed": False,
            **_safety(),
        }

    observations = [_check_observation(s) for s in rows]
    status_counts = Counter(o["capture_status"] for o in observations)
    state_counts = Counter(o["state"] for o in observations)

    return {
        "setup": SETUP,
        "status": "EXACT_MANAGEMENT_AUDIT_COMPLETED",
        "deduplication": DEDUPLICATION,
        "exact_candles": len(exact),
        "management_evidence_rows": len(observations),
        "captured_observations": status_counts.get("CAPTURED", 0),
        "not_eligible_observations": status_counts.get("NOT_ELIGIBLE", 0),
        "capture_status_counts": dict(sorted(status_counts.items())),
        "state_counts": dict(sorted(state_counts.items())),
        "stop_improvement_count": sum(o["stop_improved"] for o in observations),
        "stop_loosened_count": sum(o["stop_loosened"] for o in observations),
        "structural_advance_count": sum(
            o["structural_advance_confirmed"] for o in observations
        ),
        "trailing_active_count": sum(o["trailing_active"] for o in observations),
        "capture_inconsistency_count": sum(
            not o["capture_consistent"] for o in observations
        ),
        "observations": observations,
        "hypothesis_freeze_allowed": False,
        **_safety(),
    }


def audit_sessions(payloads):
    sessions = []
    accepted = rejected = 0
    exact_candles = management_rows = captured = 0
    improvements = loosened = structural = inconsistencies = 0
    state_counts = Counter()
    capture_status_counts = Counter()

    for index, payload in enumerate(payloads):
        report = audit_payload(payload)
        sessions.append({"session_index": index, **report})

        if report.get("status") == "EXACT_MANAGEMENT_AUDIT_COMPLETED":
            accepted += 1
            exact_candles += int(report.get("exact_candles", 0))
            management_rows += int(report.get("management_evidence_rows", 0))
            captured += int(report.get("captured_observations", 0))
            improvements += int(report.get("stop_improvement_count", 0))
            loosened += int(report.get("stop_loosened_count", 0))
            structural += int(report.get("structural_advance_count", 0))
            inconsistencies += int(report.get("capture_inconsistency_count", 0))
            state_counts.update(report.get("state_counts") or {})
            capture_status_counts.update(report.get("capture_status_counts") or {})
        else:
            rejected += 1

    return {
        "setup": SETUP,
        "status": "MULTI_SESSION_EXACT_MANAGEMENT_AUDIT_COMPLETED",
        "deduplication": DEDUPLICATION,
        "accepted_session_count": accepted,
        "rejected_session_count": rejected,
        "exact_candles": exact_candles,
        "management_evidence_rows": management_rows,
        "captured_observations": captured,
        "stop_improvement_count": improvements,
        "stop_loosened_count": loosened,
        "structural_advance_count": structural,
        "capture_inconsistency_count": inconsistencies,
        "capture_status_counts": dict(sorted(capture_status_counts.items())),
        "state_counts": dict(sorted(state_counts.items())),
        "performance_validated": False,
        "promotion_allowed": False,
        "hypothesis_freeze_allowed": False,
        "sessions": sessions,
        **_safety(),
    }


def audit(paths):
    payloads = [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for path in paths
    ]
    return audit_sessions(payloads)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = audit(args.paths)
    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
