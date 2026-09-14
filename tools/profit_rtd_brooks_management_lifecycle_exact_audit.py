"""
tools/profit_rtd_brooks_management_lifecycle_exact_audit.py

Exact audit da Stage 2 — Brooks Dynamic Management / Trade Lifecycle.

Valida consistencia estrutural do lifecycle.
Nao valida performance, PnL, predictive edge, partials ou outcomes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SETUP_NAME = "BROOKS_MANAGEMENT_LIFECYCLE_EXACT_AUDIT_V1"
TOLERANCE = 1e-9


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
        "performance_claim_allowed": False,
        "hypothesis_freeze_allowed": False,
        "dynamic_management_validated": False,
    }


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _eq(a, b):
    return abs(float(a) - float(b)) <= TOLERANCE


def _audit_episode(episode):
    inconsistencies = []

    episode_id = str(episode.get("episode_id") or "")
    entry_candle_id = str(episode.get("entry_event_candle_id") or "")
    direction = str(episode.get("direction") or "").upper()

    entry_price = _float(episode.get("entry_price"))
    initial_stop = _float(episode.get("initial_stop"))
    current_stop_final = _float(episode.get("current_stop"))
    declared_revisions = int(episode.get("stop_revision_count") or 0)
    observations = episode.get("observations") or []

    expected_episode_id = (
        f"{entry_candle_id}|{direction}"
        if entry_candle_id and direction
        else ""
    )

    if not episode_id:
        inconsistencies.append("MISSING_EPISODE_ID")
    if not entry_candle_id:
        inconsistencies.append("MISSING_ENTRY_EVENT_CANDLE_ID")
    if direction not in {"BUY", "SELL"}:
        inconsistencies.append("INVALID_DIRECTION")
    if expected_episode_id and episode_id != expected_episode_id:
        inconsistencies.append("EPISODE_ID_MISMATCH")
    if entry_price <= 0:
        inconsistencies.append("INVALID_ENTRY_PRICE")
    if initial_stop <= 0:
        inconsistencies.append("INVALID_INITIAL_STOP")
    if direction == "BUY" and initial_stop >= entry_price:
        inconsistencies.append("BUY_INITIAL_STOP_GEOMETRY_INVALID")
    if direction == "SELL" and initial_stop <= entry_price:
        inconsistencies.append("SELL_INITIAL_STOP_GEOMETRY_INVALID")

    expected_previous = initial_stop
    counted_revisions = 0
    advance_observations = 0

    for index, observation in enumerate(observations):
        prefix = f"OBS_{index}"

        previous_stop = _float(observation.get("previous_stop"))
        proposed_stop = _float(observation.get("proposed_stop"))
        current_stop_after = _float(observation.get("current_stop_after"))
        state = str(observation.get("state") or "")
        revision_applied = bool(observation.get("revision_applied"))

        if not _eq(previous_stop, expected_previous):
            inconsistencies.append(
                f"{prefix}_PREVIOUS_STOP_CHAIN_BROKEN"
            )

        if revision_applied:
            counted_revisions += 1
            advance_observations += 1

            if state != "TRAILING_STOP_ADVANCE":
                inconsistencies.append(
                    f"{prefix}_REVISION_WITHOUT_ADVANCE_STATE"
                )

            if direction == "BUY":
                if not proposed_stop > previous_stop + TOLERANCE:
                    inconsistencies.append(
                        f"{prefix}_BUY_PROPOSED_STOP_NOT_TIGHTER"
                    )
                if not current_stop_after > previous_stop + TOLERANCE:
                    inconsistencies.append(
                        f"{prefix}_BUY_APPLIED_STOP_NOT_TIGHTER"
                    )

            elif direction == "SELL":
                if not proposed_stop < previous_stop - TOLERANCE:
                    inconsistencies.append(
                        f"{prefix}_SELL_PROPOSED_STOP_NOT_TIGHTER"
                    )
                if not current_stop_after < previous_stop - TOLERANCE:
                    inconsistencies.append(
                        f"{prefix}_SELL_APPLIED_STOP_NOT_TIGHTER"
                    )

            if not _eq(current_stop_after, proposed_stop):
                inconsistencies.append(
                    f"{prefix}_APPLIED_STOP_DIFFERS_FROM_PROPOSED"
                )

        else:
            if not _eq(current_stop_after, previous_stop):
                inconsistencies.append(
                    f"{prefix}_STOP_CHANGED_WITHOUT_REVISION"
                )

        if direction == "BUY":
            if current_stop_after + TOLERANCE < previous_stop:
                inconsistencies.append(f"{prefix}_BUY_STOP_LOOSENED")
            if current_stop_after + TOLERANCE < initial_stop:
                inconsistencies.append(f"{prefix}_BUY_STOP_BELOW_INITIAL")

        elif direction == "SELL":
            if current_stop_after - TOLERANCE > previous_stop:
                inconsistencies.append(f"{prefix}_SELL_STOP_LOOSENED")
            if current_stop_after - TOLERANCE > initial_stop:
                inconsistencies.append(f"{prefix}_SELL_STOP_ABOVE_INITIAL")

        expected_previous = current_stop_after

    if declared_revisions != counted_revisions:
        inconsistencies.append("STOP_REVISION_COUNT_MISMATCH")

    if observations:
        if not _eq(current_stop_final, expected_previous):
            inconsistencies.append("FINAL_CURRENT_STOP_MISMATCH")
    else:
        if not _eq(current_stop_final, initial_stop):
            inconsistencies.append(
                "EMPTY_EPISODE_CURRENT_STOP_NOT_INITIAL"
            )

    return {
        "episode_id": episode_id,
        "entry_event_candle_id": entry_candle_id,
        "direction": direction,
        "observation_count": len(observations),
        "declared_stop_revision_count": declared_revisions,
        "counted_stop_revision_count": counted_revisions,
        "advance_observations": advance_observations,
        "final_current_stop": current_stop_final,
        "inconsistency_count": len(inconsistencies),
        "inconsistencies": inconsistencies,
    }


def audit_lifecycle_report(payload):
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")

    sessions = payload.get("sessions")
    if isinstance(sessions, list):
        episodes = []
        for session in sessions:
            if isinstance(session, dict):
                episodes.extend(session.get("episodes") or [])
        accepted_session_count = len(sessions)
    else:
        episodes = payload.get("episodes") or []
        accepted_session_count = 1

    episode_reports = [
        _audit_episode(episode)
        for episode in episodes
        if isinstance(episode, dict)
    ]

    inconsistency_count = sum(
        item["inconsistency_count"] for item in episode_reports
    )
    episodes_with_advance = sum(
        1
        for item in episode_reports
        if item["counted_stop_revision_count"] > 0
    )
    advance_observations = sum(
        item["advance_observations"] for item in episode_reports
    )
    observation_count = sum(
        item["observation_count"] for item in episode_reports
    )

    if inconsistency_count > 0:
        status = "LIFECYCLE_INCONSISTENCY_DETECTED"
    elif not episode_reports:
        status = "MORE_EVIDENCE_REQUIRED"
    else:
        status = "LIFECYCLE_EXACT_AUDIT_COMPLETED"

    return {
        "setup": SETUP_NAME,
        "status": status,
        "accepted_session_count": accepted_session_count,
        "episode_count": len(episode_reports),
        "observation_count": observation_count,
        "episodes_with_stop_advance": episodes_with_advance,
        "stop_advance_observations": advance_observations,
        "lifecycle_inconsistency_count": inconsistency_count,
        "validation_reason": (
            "STRUCTURAL_LIFECYCLE_CONSISTENCY_ONLY_NO_PERFORMANCE_CLAIM"
        ),
        "episodes": episode_reports,
        **_safety(),
    }


def audit_file(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    report = audit_lifecycle_report(payload)
    report["source"] = str(path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Exact audit Brooks management lifecycle."
    )
    parser.add_argument("path")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = audit_file(args.path)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("status=", report["status"])
    print("accepted_session_count=", report["accepted_session_count"])
    print("episode_count=", report["episode_count"])
    print("observation_count=", report["observation_count"])
    print("episodes_with_stop_advance=", report["episodes_with_stop_advance"])
    print("stop_advance_observations=", report["stop_advance_observations"])
    print("lifecycle_inconsistency_count=", report["lifecycle_inconsistency_count"])
    print("dynamic_management_validated=", report["dynamic_management_validated"])

    return 0 if report["lifecycle_inconsistency_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
