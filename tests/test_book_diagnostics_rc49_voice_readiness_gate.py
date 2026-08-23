from analysis.replay.book_diagnostics_voice_readiness_gate import BookDiagnosticsVoiceReadinessGate


def _diag(ready=True):
    return {
        "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
        "ready_for_real_audio": ready,
        "readonly": True,
        "affects_decision": False,
    }


def _test(executed=True, completed=True, error=""):
    return {
        "version": "RC47-CONTROLLED-REAL-AUDIO-TEST",
        "executed": executed,
        "completed": completed,
        "error": error,
        "readonly": True,
        "affects_decision": False,
    }


def test_blocks_when_diagnostics_not_ready():
    result = BookDiagnosticsVoiceReadinessGate().evaluate(diagnostics=_diag(False))
    assert result.operational_voice_allowed is False
    assert result.reason == "DIAGNOSTICS_NOT_READY"


def test_requires_controlled_test_after_ready_diagnostics():
    result = BookDiagnosticsVoiceReadinessGate().evaluate(diagnostics=_diag(True))
    assert result.diagnostics_ready is True
    assert result.controlled_test_passed is False
    assert result.reason == "CONTROLLED_TEST_REQUIRED"


def test_blocks_failed_controlled_test():
    result = BookDiagnosticsVoiceReadinessGate().evaluate(
        diagnostics=_diag(True), controlled_test=_test(completed=False)
    )
    assert result.operational_voice_allowed is False
    assert result.reason == "CONTROLLED_TEST_NOT_PASSED"


def test_blocks_controlled_test_with_error():
    result = BookDiagnosticsVoiceReadinessGate().evaluate(
        diagnostics=_diag(True), controlled_test=_test(error="audio failure")
    )
    assert result.operational_voice_allowed is False


def test_allows_only_after_both_steps_pass():
    result = BookDiagnosticsVoiceReadinessGate().evaluate(
        diagnostics=_diag(True), controlled_test=_test()
    )
    assert result.operational_voice_allowed is True
    assert result.reason == "READY"


def test_require_operational_ready_raises_when_blocked():
    gate = BookDiagnosticsVoiceReadinessGate()
    try:
        gate.require_operational_ready(diagnostics=_diag(False))
    except PermissionError as exc:
        assert "DIAGNOSTICS_NOT_READY" in str(exc)
    else:
        raise AssertionError("PermissionError expected")


def test_rejects_wrong_diagnostics_version():
    bad = _diag(True)
    bad["version"] = "BAD"
    try:
        BookDiagnosticsVoiceReadinessGate().evaluate(diagnostics=bad)
    except PermissionError:
        pass
    else:
        raise AssertionError("PermissionError expected")


def test_rejects_decision_affecting_contracts():
    bad = _diag(True)
    bad["affects_decision"] = True
    try:
        BookDiagnosticsVoiceReadinessGate().evaluate(diagnostics=bad)
    except PermissionError:
        pass
    else:
        raise AssertionError("PermissionError expected")


def test_snapshot_is_readonly_and_non_operational():
    result = BookDiagnosticsVoiceReadinessGate().evaluate(
        diagnostics=_diag(True), controlled_test=_test()
    )
    payload = result.to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False
