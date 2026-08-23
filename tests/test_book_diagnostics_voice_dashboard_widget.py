from __future__ import annotations

import pytest

from analysis.replay.book_diagnostics_voice_dashboard_widget import (
    BookDiagnosticsVoiceDashboardWidgetBuilder,
)


def projection(**overrides):
    payload = {
        "version": "RC58-VOICE-HEALTH-DASHBOARD-PROJECTION",
        "status": "READY",
        "label": "Voz pronta",
        "summary": "Voice integration is ready with backend WINDOWS_SAPI.",
        "backend": "WINDOWS_SAPI",
        "backend_healthy": True,
        "operational_voice_allowed": True,
        "readiness_reason": "READY",
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(overrides)
    return payload


def test_builds_widget_from_rc58_projection():
    result = BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection())
    assert result.version == "RC60-DASHBOARD-VOICE-WIDGET-CONTRACT"
    assert result.title == "Voice Assistant"
    assert result.status == "READY"
    assert result.label == "Voz pronta"


def test_preserves_backend_and_health():
    result = BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection())
    assert result.backend == "WINDOWS_SAPI"
    assert result.backend_healthy is True


def test_preserves_operational_flag():
    result = BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection())
    assert result.operational_voice_allowed is True


def test_detail_comes_from_summary():
    result = BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection(summary="Resumo"))
    assert result.detail == "Resumo"


def test_widget_is_readonly_and_observational():
    result = BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection())
    assert result.readonly is True
    assert result.affects_decision is False


def test_to_dict_preserves_contract():
    payload = BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection()).to_dict()
    assert payload["version"] == "RC60-DASHBOARD-VOICE-WIDGET-CONTRACT"
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_rejects_wrong_source_version():
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection(version="OTHER"))


def test_rejects_non_readonly_projection():
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection(readonly=False))


def test_rejects_decision_affecting_projection():
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection(affects_decision=True))


def test_rejects_empty_label():
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceDashboardWidgetBuilder().build(projection(label=""))
