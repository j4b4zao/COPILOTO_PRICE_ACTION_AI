from analysis.replay.book_diagnostics_voice_health_report import BookDiagnosticsVoiceHealthReporter


def _status(**overrides):
    payload = {
        "version": "RC55-VOICE-INTEGRATION-STATUS",
        "service_enabled": True,
        "service_available": True,
        "backend": "WINDOWS_SAPI",
        "backend_healthy": True,
        "diagnostics_ready": True,
        "readiness_reason": "READY",
        "operational_voice_allowed": True,
        "orchestrator_initialized": False,
        "queue_size": 0,
        "session_state": "IDLE",
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(overrides)
    return payload


def test_ready_status():
    report = BookDiagnosticsVoiceHealthReporter().build(_status())
    assert report.status == "READY"
    assert report.operational_voice_allowed is True


def test_disabled_status():
    report = BookDiagnosticsVoiceHealthReporter().build(_status(service_enabled=False))
    assert report.status == "DISABLED"


def test_runtime_unavailable_is_degraded():
    report = BookDiagnosticsVoiceHealthReporter().build(_status(service_available=False))
    assert report.status == "DEGRADED"


def test_unhealthy_backend_is_degraded():
    report = BookDiagnosticsVoiceHealthReporter().build(_status(backend_healthy=False))
    assert report.status == "DEGRADED"


def test_diagnostics_pending():
    report = BookDiagnosticsVoiceHealthReporter().build(_status(diagnostics_ready=False))
    assert report.status == "DIAGNOSTICS_PENDING"


def test_controlled_test_required():
    report = BookDiagnosticsVoiceHealthReporter().build(
        _status(operational_voice_allowed=False, readiness_reason="CONTROLLED_TEST_REQUIRED")
    )
    assert report.status == "TEST_REQUIRED"


def test_other_readiness_block_is_degraded():
    report = BookDiagnosticsVoiceHealthReporter().build(
        _status(operational_voice_allowed=False, readiness_reason="CONTROLLED_TEST_NOT_PASSED")
    )
    assert report.status == "DEGRADED"


def test_report_is_readonly_and_observational():
    payload = BookDiagnosticsVoiceHealthReporter().build(_status()).to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_invalid_version_rejected():
    try:
        BookDiagnosticsVoiceHealthReporter().build(_status(version="INVALID"))
    except PermissionError:
        pass
    else:
        raise AssertionError("invalid RC55 version must be rejected")


def test_decision_affecting_input_rejected():
    try:
        BookDiagnosticsVoiceHealthReporter().build(_status(affects_decision=True))
    except PermissionError:
        pass
    else:
        raise AssertionError("decision-affecting input must be rejected")
