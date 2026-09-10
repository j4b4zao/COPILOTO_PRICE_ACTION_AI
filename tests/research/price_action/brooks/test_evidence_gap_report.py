import pytest

from tools.profit_rtd_brooks_evidence_gap_report import build_report


def _suite():
    return {
        "suite": "BROOKS_RESEARCH_EVIDENCE_SUITE_V1",
        "mode": "SELECTION",
        "eligible_sessions": 2,
        "rejected_sessions": [],
        "setups": {
            "DIRECT": {
                "status": "MORE_EVIDENCE_REQUIRED",
                "eligible_sessions": 2,
                "complete_sequences": 0,
                "sessions": [
                    {
                        "exact_candles": 9,
                        "incomplete_candidates": 1,
                        "incomplete": [{"reasons": ["RANGE"]}],
                        "producer_phase_coverage": {
                            "observed_breakout_phases": ["BREAKOUT_PENDING"]
                        },
                    },
                    {"exact_candles": 8, "incomplete_candidates": 0},
                ],
            },
            "ADAPTED": {
                "status": "MULTI_SESSION_AUDIT_COMPLETED",
                "accepted_session_count": 1,
                "accepted_sessions": [
                    {
                        "audit": {
                            "sequence_count": 2,
                            "matched_sequence_count": 0,
                            "sequences": [{"reason": "FAILURE_NOT_OBSERVED"}] * 2,
                        }
                    }
                ],
            },
            "MANAGEMENT": {
                "status": "CLASSIFIER_ONLY_NO_EXACT_AUDITOR",
                "eligible_sessions": 2,
            },
        },
    }


def test_report_quantifies_direct_and_adapted_gaps():
    report = build_report(_suite())
    assert report["families"]["DIRECT"]["exact_candles"] == 17
    assert report["families"]["DIRECT"]["candidate_sequences"] == 1
    assert report["families"]["DIRECT"]["gap"] == "NO_COMPLETE_SEQUENCE"
    assert report["families"]["ADAPTED"]["candidate_sequences"] == 2
    assert report["families"]["ADAPTED"]["gap"] == "NO_MATCHED_SEQUENCE"
    assert report["families"]["MANAGEMENT"]["gap"] == "EXACT_CANDLE_AUDITOR_NOT_AVAILABLE"


def test_report_keeps_all_operational_influence_disabled():
    report = build_report(_suite())
    for key in (
        "hypothesis_freeze_allowed", "oos_collection_allowed", "promotion_allowed",
        "score_influence_allowed", "risk_influence_allowed", "decision_influence_allowed",
        "alert_influence_allowed", "order_execution_allowed",
    ):
        assert report[key] is False


def test_report_rejects_oos_or_unknown_suite():
    payload = _suite()
    payload["mode"] = "OOS"
    with pytest.raises(ValueError, match="SELECTION"):
        build_report(payload)
    payload["mode"] = "SELECTION"
    payload["suite"] = "UNKNOWN"
    with pytest.raises(ValueError, match="unsupported"):
        build_report(payload)
