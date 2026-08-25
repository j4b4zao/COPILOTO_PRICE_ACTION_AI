"""Tests for BookDiagnostics RC61 dashboard widget service integration."""

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def build_service(enabled: bool = False):
    return BookDiagnosticsVoiceService(config=VoiceConfig(enabled=enabled, backend="NULL_TTS"))


def test_dashboard_widget_returns_rc60_contract():
    widget = build_service().dashboard_widget()
    assert widget.version == "RC60-DASHBOARD-VOICE-WIDGET-CONTRACT"
    assert widget.readonly is True
    assert widget.affects_decision is False


def test_dashboard_widget_disabled_state():
    widget = build_service().dashboard_widget()
    assert widget.status == "DISABLED"
    assert widget.label == "Voz desativada"
    assert widget.backend == "DISABLED"


def test_dashboard_widget_preserves_title():
    widget = build_service().dashboard_widget()
    assert widget.title == "Voice Assistant"


def test_dashboard_widget_does_not_initialize_orchestrator():
    service = build_service()
    assert service._orchestrator is None
    service.dashboard_widget()
    assert service._orchestrator is None


def test_dashboard_widget_does_not_store_audio_validation():
    service = build_service()
    assert service._last_controlled_audio_test is None
    service.dashboard_widget()
    assert service._last_controlled_audio_test is None


def test_dashboard_widget_to_dict_is_readonly():
    payload = build_service().dashboard_widget().to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_dashboard_widget_has_no_audio_execution_methods():
    widget = build_service().dashboard_widget()
    assert not hasattr(widget, "speak")
    assert not hasattr(widget, "test_audio")
    assert not hasattr(widget, "dispatch")


def test_dashboard_widget_repeated_calls_are_stable():
    service = build_service()
    first = service.dashboard_widget().to_dict()
    second = service.dashboard_widget().to_dict()
    assert first == second


def test_dashboard_widget_operational_flag_defaults_false():
    widget = build_service().dashboard_widget()
    assert widget.operational_voice_allowed is False


def test_dashboard_widget_service_keeps_core_isolation_flags():
    widget = build_service().dashboard_widget()
    payload = widget.to_dict()
    assert payload["affects_decision"] is False
    assert payload["readonly"] is True
