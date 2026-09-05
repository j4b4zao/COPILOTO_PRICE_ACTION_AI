import json

from tools.profit_rtd_brooks_selection_outcome import classify_path, classify_report


def _report(**overrides):
    report = {
        "mode": "SELECTION",
        "requested_sessions": 1,
        "produced_session_files": 1,
        "manifest": {
            "eligible_sessions": 1,
            "rejected_sessions": 0,
            "selection_cutoff": None,
        },
    }
    report.update(overrides)
    return report


def test_valid_selection_counts_as_selection_evidence():
    result = classify_report(_report())
    assert result["status"] == "VALID_SELECTION"
    assert result["counts_as_selection_evidence"] is True
    assert result["counts_as_oos_evidence"] is False


def test_no_valid_source_matches_weekend_fail_closed_case():
    result = classify_report(_report(
        produced_session_files=0,
        manifest={"eligible_sessions": 0, "rejected_sessions": 0, "selection_cutoff": None},
    ))
    assert result["status"] == "NO_VALID_SOURCE"
    assert result["counts_as_selection_evidence"] is False
    assert result["retry_when_real_source_active"] is True


def test_manifest_rejection_is_rejected():
    result = classify_report(_report(
        manifest={"eligible_sessions": 0, "rejected_sessions": 1, "selection_cutoff": None},
    ))
    assert result["status"] == "REJECTED"
    assert "MANIFEST_REJECTIONS_PRESENT" in result["reasons"]


def test_wrong_mode_is_rejected():
    result = classify_report(_report(mode="OOS"))
    assert result["status"] == "REJECTED"
    assert result["counts_as_oos_evidence"] is False


def test_partial_collection_is_incomplete():
    result = classify_report(_report(requested_sessions=2, produced_session_files=1))
    assert result["status"] == "INCOMPLETE"
    assert result["counts_as_selection_evidence"] is False


def test_operational_isolation_is_preserved():
    result = classify_report(_report())
    for flag in (
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
        "hypothesis_freeze_allowed",
    ):
        assert result[flag] is False


def test_classify_path_round_trip(tmp_path):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(_report()), encoding="utf-8")
    result = classify_path(path)
    assert result["status"] == "VALID_SELECTION"
    assert result["source_report"] == str(path)


def test_invalid_report_type_fails_closed():
    try:
        classify_report([])
    except TypeError as exc:
        assert "dict" in str(exc)
    else:
        raise AssertionError("TypeError expected")
