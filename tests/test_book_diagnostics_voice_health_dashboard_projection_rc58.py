from analysis.replay.book_diagnostics_voice_health_dashboard_projection import (
    BookDiagnosticsVoiceHealthDashboardProjector,
)


def report(status="DISABLED", **updates):
    data = {
        "version": "RC56-VOICE-INTEGRATION-HEALTH-REPORT",
        "status": status,
        "summary": "summary",
        "backend": "NULL_TTS",
        "backend_healthy": True,
        "operational_voice_allowed": False,
        "readiness_reason": "CONTROLLED_TEST_REQUIRED",
        "readonly": True,
        "affects_decision": False,
    }
    data.update(updates)
    return data


def test_projects_disabled():
    out = BookDiagnosticsVoiceHealthDashboardProjector().project(report())
    assert out.status == "DISABLED"
    assert out.label == "Voz desativada"


def test_projects_diagnostics_pending():
    out = BookDiagnosticsVoiceHealthDashboardProjector().project(report("DIAGNOSTICS_PENDING"))
    assert out.label == "Diagnostico pendente"


def test_projects_test_required():
    out = BookDiagnosticsVoiceHealthDashboardProjector().project(report("TEST_REQUIRED"))
    assert out.label == "Teste de audio necessario"


def test_projects_ready():
    out = BookDiagnosticsVoiceHealthDashboardProjector().project(report("READY", operational_voice_allowed=True))
    assert out.label == "Voz pronta"
    assert out.operational_voice_allowed is True


def test_projects_degraded():
    out = BookDiagnosticsVoiceHealthDashboardProjector().project(report("DEGRADED", backend_healthy=False))
    assert out.label == "Voz degradada"


def test_preserves_backend_and_summary():
    out = BookDiagnosticsVoiceHealthDashboardProjector().project(report(backend="WINDOWS_SAPI", summary="ok"))
    assert out.backend == "WINDOWS_SAPI"
    assert out.summary == "ok"


def test_output_is_readonly_and_observational():
    out = BookDiagnosticsVoiceHealthDashboardProjector().project(report())
    payload = out.to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_rejects_wrong_source_version():
    bad = report(); bad["version"] = "RC55"
    try:
        BookDiagnosticsVoiceHealthDashboardProjector().project(bad)
        assert False
    except PermissionError:
        pass


def test_rejects_decision_affecting_source():
    try:
        BookDiagnosticsVoiceHealthDashboardProjector().project(report(affects_decision=True))
        assert False
    except PermissionError:
        pass


def test_rejects_unknown_status():
    try:
        BookDiagnosticsVoiceHealthDashboardProjector().project(report("UNKNOWN"))
        assert False
    except ValueError:
        pass
