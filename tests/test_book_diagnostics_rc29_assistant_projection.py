from analysis.replay.book_diagnostics_assistant_projection import BookDiagnosticsAssistantProjector


def _snapshot(*, caution=False, block=False):
    checklist = {}
    if caution:
        checklist["tight_range"] = {
            "passed": False,
            "severity": "CAUTION",
            "message": "Range apertado",
        }
    if block:
        checklist["poor_environment"] = {
            "passed": False,
            "severity": "BLOCK",
            "message": "Ambiente ruim",
        }
    return {
        "version": "RC28-NON-INVASIVE-CORE-RECEIVERS",
        "readonly": True,
        "affects_decision": False,
        "evidence": {
            "trend_strength": {"weighted_value": 0.8},
            "breakout_strength": {"weighted_value": 0.6},
        },
        "context": {
            "market_environment": {"state": "TIGHT_RANGE"},
            "trend_control": {"state": "STRONG_CONTROL"},
        },
        "checklist": checklist,
    }


def test_projection_builds_operator_friendly_summary():
    result = BookDiagnosticsAssistantProjector().build(_snapshot())
    assert result.caution_level == "LOW"
    assert result.evidence_count == 2
    assert result.context_count == 2
    assert result.readonly is True
    assert result.affects_decision is False
    assert "tight range" in result.market_summary.lower()


def test_caution_failure_sets_medium_level_and_voice_prefix():
    result = BookDiagnosticsAssistantProjector().build(_snapshot(caution=True))
    assert result.caution_level == "MEDIUM"
    assert result.voice_text.startswith("Cautela.")
    assert "1 cautelas" in result.checklist_summary


def test_block_failure_is_informational_high_caution():
    result = BookDiagnosticsAssistantProjector().build(_snapshot(block=True))
    assert result.caution_level == "HIGH"
    assert result.voice_text.startswith("Atencao.")
    assert result.affects_decision is False


def test_empty_snapshot_is_supported():
    payload = {
        "version": "RC28-NON-INVASIVE-CORE-RECEIVERS",
        "readonly": True,
        "affects_decision": False,
        "evidence": {},
        "context": {},
        "checklist": {},
    }
    result = BookDiagnosticsAssistantProjector().build(payload)
    assert result.headline == "Contexto experimental ainda insuficiente."
    assert result.caution_level == "LOW"


def test_rejects_decision_affecting_snapshot():
    payload = _snapshot()
    payload["affects_decision"] = True
    try:
        BookDiagnosticsAssistantProjector().build(payload)
    except PermissionError:
        return
    raise AssertionError("decision-affecting snapshot should be rejected")


def test_rejects_wrong_origin_version():
    payload = _snapshot()
    payload["version"] = "OTHER"
    try:
        BookDiagnosticsAssistantProjector().build(payload)
    except PermissionError:
        return
    raise AssertionError("wrong origin version should be rejected")


if __name__ == "__main__":
    test_projection_builds_operator_friendly_summary()
    test_caution_failure_sets_medium_level_and_voice_prefix()
    test_block_failure_is_informational_high_caution()
    test_empty_snapshot_is_supported()
    test_rejects_decision_affecting_snapshot()
    test_rejects_wrong_origin_version()
    print("RC29 assistant projection tests: OK")
