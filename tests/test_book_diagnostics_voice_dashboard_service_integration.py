from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def test_dashboard_projection_exists_and_is_rc58():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    result = service.dashboard_projection()
    assert result.version == "RC58-VOICE-HEALTH-DASHBOARD-PROJECTION"
    assert result.status == "DISABLED"
    assert result.label == "Voz desativada"


def test_dashboard_projection_is_readonly_and_non_decision_affecting():
    result = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).dashboard_projection()
    payload = result.to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_dashboard_projection_does_not_initialize_orchestrator():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    assert service._orchestrator is None
    service.dashboard_projection()
    assert service._orchestrator is None


def test_dashboard_projection_does_not_enable_service():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    service.dashboard_projection()
    assert service.enabled is False


def test_dashboard_projection_preserves_disabled_backend():
    result = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).dashboard_projection()
    assert result.backend == "DISABLED"
    assert result.backend_healthy is False


def test_dashboard_projection_returns_fresh_value_without_side_effects():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    one = service.dashboard_projection().to_dict()
    two = service.dashboard_projection().to_dict()
    assert one == two
    assert service._orchestrator is None


def test_dashboard_projection_matches_health_report_status():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    health = service.health_report()
    dashboard = service.dashboard_projection()
    assert dashboard.status == health.status
    assert dashboard.summary == health.summary
    assert dashboard.readiness_reason == health.readiness_reason


def test_dashboard_projection_operational_flag_is_false_without_validation():
    result = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).dashboard_projection()
    assert result.operational_voice_allowed is False


def test_dashboard_projection_has_expected_public_contract():
    payload = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).dashboard_projection().to_dict()
    assert set(payload) == {
        "version",
        "status",
        "label",
        "summary",
        "backend",
        "backend_healthy",
        "operational_voice_allowed",
        "readiness_reason",
        "readonly",
        "affects_decision",
    }


def test_dashboard_projection_does_not_expose_audio_execution_methods():
    projection = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).dashboard_projection()
    assert not hasattr(projection, "speak")
    assert not hasattr(projection, "test_audio")
    assert not hasattr(projection, "dispatch")
