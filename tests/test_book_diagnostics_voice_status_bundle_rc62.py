from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService
from analysis.replay.book_diagnostics_voice_status_bundle import (
    BookDiagnosticsVoiceStatusBundleBuilder,
)


def test_rc62_service_returns_bundle():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    bundle = service.status_bundle()
    assert bundle.version == "RC62-VOICE-STATUS-BUNDLE"


def test_rc62_bundle_is_readonly_and_non_decision():
    bundle = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).status_bundle()
    assert bundle.readonly is True
    assert bundle.affects_decision is False


def test_rc62_contains_all_three_contracts():
    bundle = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).status_bundle().to_dict()
    assert bundle["health_report"]["version"] == "RC56-VOICE-INTEGRATION-HEALTH-REPORT"
    assert bundle["dashboard_projection"]["version"] == "RC58-VOICE-HEALTH-DASHBOARD-PROJECTION"
    assert bundle["dashboard_widget"]["version"] == "RC60-DASHBOARD-VOICE-WIDGET-CONTRACT"


def test_rc62_status_is_consistent_across_payloads():
    bundle = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).status_bundle().to_dict()
    statuses = {
        bundle["health_report"]["status"],
        bundle["dashboard_projection"]["status"],
        bundle["dashboard_widget"]["status"],
    }
    assert statuses == {"DISABLED"}


def test_rc62_does_not_initialize_orchestrator():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    assert service._orchestrator is None
    service.status_bundle()
    assert service._orchestrator is None


def test_rc62_bundle_has_no_audio_execution_methods():
    bundle = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False)).status_bundle()
    assert not hasattr(bundle, "speak")
    assert not hasattr(bundle, "test_audio")
    assert not hasattr(bundle, "dispatch")


def test_rc62_rejects_invalid_health_contract():
    builder = BookDiagnosticsVoiceStatusBundleBuilder()
    projection = {
        "version": builder.PROJECTION_VERSION,
        "status": "DISABLED",
        "readonly": True,
        "affects_decision": False,
    }
    widget = {
        "version": builder.WIDGET_VERSION,
        "status": "DISABLED",
        "readonly": True,
        "affects_decision": False,
    }
    try:
        builder.build(health_report={}, dashboard_projection=projection, dashboard_widget=widget)
    except PermissionError:
        pass
    else:
        raise AssertionError("invalid health contract must be rejected")


def test_rc62_rejects_status_mismatch():
    builder = BookDiagnosticsVoiceStatusBundleBuilder()
    health = {
        "version": builder.HEALTH_VERSION,
        "status": "READY",
        "readonly": True,
        "affects_decision": False,
    }
    projection = {
        "version": builder.PROJECTION_VERSION,
        "status": "DEGRADED",
        "readonly": True,
        "affects_decision": False,
    }
    widget = {
        "version": builder.WIDGET_VERSION,
        "status": "DEGRADED",
        "readonly": True,
        "affects_decision": False,
    }
    try:
        builder.build(health_report=health, dashboard_projection=projection, dashboard_widget=widget)
    except ValueError:
        pass
    else:
        raise AssertionError("status mismatch must be rejected")


def test_rc62_repeated_calls_are_stable():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    assert service.status_bundle().to_dict() == service.status_bundle().to_dict()


def test_rc62_disabled_service_stays_disabled():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    service.status_bundle()
    assert service.enabled is False
