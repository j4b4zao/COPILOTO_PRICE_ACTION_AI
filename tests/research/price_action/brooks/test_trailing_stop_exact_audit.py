"""Tests for Brooks trailing-stop exact audit."""

from tools.profit_rtd_brooks_trailing_stop_exact_audit import (
    audit_many,
    audit_session,
)


def sample(candle_id, **pa_overrides):
    pa = {
        "brooks_management_capture_status": "CAPTURED",
        "brooks_management_state": "PROTECTIVE_STOP_HOLD",
        "brooks_management_direction": "BUY",
        "brooks_management_initial_stop": 95.0,
        "brooks_management_current_stop": 95.0,
        "brooks_management_proposed_stop": 95.0,
        "brooks_management_trailing_active": False,
        "brooks_management_stop_improved": False,
        "brooks_management_stop_loosened": False,
        "brooks_management_structural_advance_confirmed": False,
    }
    pa.update(pa_overrides)

    return {
        "candle_evidence": {
            "candle_id": candle_id,
        },
        "price_action": pa,
    }


def test_exact_audit_deduplicates_last_revision():
    cid = "WINV26|M1|2026-09-12T10:00:00"

    payload = {
        "samples": [
            sample(cid),
            sample(
                cid,
                brooks_management_state="TRAILING_STOP_ADVANCE",
                brooks_management_proposed_stop=99.0,
                brooks_management_trailing_active=True,
                brooks_management_stop_improved=True,
                brooks_management_structural_advance_confirmed=True,
            ),
        ]
    }

    report = audit_session(payload)

    assert report["raw_samples"] == 2
    assert report["exact_candles"] == 1
    assert report["trailing_advance_observations"] == 1
    assert report["capture_inconsistency_count"] == 0


def test_buy_advance_requires_tighter_stop():
    payload = {
        "samples": [
            sample(
                "WINV26|M1|2026-09-12T10:01:00",
                brooks_management_state="TRAILING_STOP_ADVANCE",
                brooks_management_proposed_stop=94.0,
                brooks_management_trailing_active=True,
                brooks_management_stop_improved=True,
                brooks_management_structural_advance_confirmed=True,
            )
        ]
    }

    report = audit_session(payload)

    assert report["status"] == "CAPTURE_INCONSISTENCY_DETECTED"
    assert report["capture_inconsistency_count"] == 1
    assert "BUY_ADVANCE_NOT_TIGHTER" in (
        report["observations"][0]["inconsistencies"]
    )


def test_hold_cannot_change_stop():
    payload = {
        "samples": [
            sample(
                "WINV26|M1|2026-09-12T10:02:00",
                brooks_management_proposed_stop=96.0,
            )
        ]
    }

    report = audit_session(payload)

    assert report["capture_inconsistency_count"] == 1
    assert "HOLD_CHANGED_STOP" in (
        report["observations"][0]["inconsistencies"]
    )


def test_no_eligible_observation_requires_more_evidence():
    payload = {
        "samples": [
            sample(
                "WINV26|M1|2026-09-12T10:03:00",
                brooks_management_capture_status="NOT_ELIGIBLE",
                brooks_management_state="NO_STOP_CONTEXT",
            )
        ]
    }

    report = audit_session(payload)

    assert report["status"] == "MORE_EVIDENCE_REQUIRED"
    assert report["eligible_trailing_observations"] == 0
    assert report["dynamic_management_validated"] is False
    assert report["hypothesis_freeze_allowed"] is False


def test_multi_session_report_keeps_research_safety():
    a = {
        "samples": [
            sample("WINV26|M1|2026-09-12T10:04:00"),
        ]
    }
    b = {
        "samples": [
            sample(
                "WINV26|M1|2026-09-12T10:05:00",
                brooks_management_state="TRAILING_STOP_ADVANCE",
                brooks_management_proposed_stop=99.0,
                brooks_management_trailing_active=True,
                brooks_management_stop_improved=True,
                brooks_management_structural_advance_confirmed=True,
            ),
        ]
    }

    report = audit_many([a, b])

    assert report["status"] == "MULTI_SESSION_EXACT_AUDIT_COMPLETED"
    assert report["accepted_session_count"] == 2
    assert report["exact_candles"] == 2
    assert report["trailing_hold_observations"] == 1
    assert report["trailing_advance_observations"] == 1
    assert report["capture_inconsistency_count"] == 0
    assert report["research_only"] is True
    assert report["risk_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["dynamic_management_validated"] is False
