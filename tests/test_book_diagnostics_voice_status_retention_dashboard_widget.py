from dataclasses import FrozenInstanceError

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_dashboard_widget import (
    BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder,
)


def projection(**overrides):
    payload = {
        "version": "RC76-VOICE-STATUS-RETENTION-DASHBOARD-PROJECTION",
        "status": "WITHIN_LIMIT",
        "label": "Retencao dentro do limite",
        "summary": "Retention is within the configured limit with 2 snapshot(s).",
        "directory": "/tmp/voice",
        "directory_exists": True,
        "prefix": "voice_status",
        "keep": 20,
        "existing_count": 2,
        "retained_count": 2,
        "excess_count": 0,
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(overrides)
    return payload


def test_builds_rc78_widget_contract():
    result = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder().build(projection())
    assert result.version == "RC78-VOICE-STATUS-RETENTION-DASHBOARD-WIDGET-CONTRACT"
    assert result.title == "Voice Status Retention"
    assert result.status == "WITHIN_LIMIT"


def test_preserves_empty_status():
    result = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder().build(
        projection(status="EMPTY", label="Sem snapshots", existing_count=0, retained_count=0)
    )
    assert result.status == "EMPTY"
    assert result.excess_count == 0


def test_preserves_over_limit_status_and_counts():
    result = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder().build(
        projection(status="OVER_LIMIT", label="Retencao acima do limite", keep=2, existing_count=5, retained_count=2, excess_count=3)
    )
    assert result.status == "OVER_LIMIT"
    assert result.excess_count == 3


def test_preserves_context_fields():
    result = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder().build(
        projection(directory="/var/log/voice", prefix="custom", keep=7)
    )
    assert result.directory == "/var/log/voice"
    assert result.prefix == "custom"
    assert result.keep == 7


def test_widget_is_readonly_and_neutral():
    result = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder().build(projection())
    assert result.readonly is True
    assert result.affects_decision is False
    with pytest.raises(FrozenInstanceError):
        result.status = "OVER_LIMIT"


def test_rejects_wrong_source_version():
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder().build(projection(version="RC75"))


def test_rejects_non_readonly_projection():
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder().build(projection(readonly=False))


def test_rejects_invalid_status_or_empty_label():
    builder = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder()
    with pytest.raises(ValueError):
        builder.build(projection(status="UNKNOWN"))
    with pytest.raises(ValueError):
        builder.build(projection(label=""))


def test_rejects_invalid_keep_or_negative_counts():
    builder = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder()
    with pytest.raises(ValueError):
        builder.build(projection(keep=0))
    with pytest.raises(ValueError):
        builder.build(projection(existing_count=-1, retained_count=-1))


def test_rejects_inconsistent_counts_and_has_no_mutation_api():
    builder = BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder()
    with pytest.raises(ValueError):
        builder.build(projection(existing_count=3, retained_count=2, excess_count=0))
    forbidden = {"speak", "test_audio", "delete", "write", "render", "dispatch"}
    assert forbidden.isdisjoint(set(dir(builder)))
