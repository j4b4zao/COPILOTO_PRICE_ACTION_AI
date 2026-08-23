import pytest

from analysis.replay.book_diagnostics_voice_status_retention_bundle import (
    BookDiagnosticsVoiceStatusRetentionBundleBuilder,
)


def _inspection(existing=0, retained=0, excess=0):
    return {
        "version": "RC70-VOICE-STATUS-RETENTION-INSPECTION",
        "directory": "/tmp/voice",
        "prefix": "voice_status",
        "keep": 2,
        "directory_exists": True,
        "existing_files": tuple(f"f{i}.json" for i in range(existing)),
        "retained_files": tuple(f"f{i}.json" for i in range(retained)),
        "would_remove_files": tuple(f"x{i}.json" for i in range(excess)),
        "readonly": True,
        "affects_decision": False,
    }


def _health(status, existing=0, retained=0, excess=0):
    return {
        "version": "RC73-VOICE-STATUS-RETENTION-HEALTH",
        "status": status,
        "summary": "ok",
        "directory": "/tmp/voice",
        "directory_exists": True,
        "prefix": "voice_status",
        "keep": 2,
        "existing_count": existing,
        "retained_count": retained,
        "would_remove_count": excess,
        "readonly": True,
        "affects_decision": False,
    }


def _projection(status, existing=0, retained=0, excess=0):
    return {
        "version": "RC76-VOICE-STATUS-RETENTION-DASHBOARD-PROJECTION",
        "status": status,
        "label": status,
        "summary": "ok",
        "directory": "/tmp/voice",
        "directory_exists": True,
        "prefix": "voice_status",
        "keep": 2,
        "existing_count": existing,
        "retained_count": retained,
        "excess_count": excess,
        "readonly": True,
        "affects_decision": False,
    }


def _widget(status, existing=0, retained=0, excess=0):
    return {
        "version": "RC78-VOICE-STATUS-RETENTION-DASHBOARD-WIDGET-CONTRACT",
        "title": "Voice Status Retention",
        "status": status,
        "label": status,
        "detail": "ok",
        "directory": "/tmp/voice",
        "directory_exists": True,
        "prefix": "voice_status",
        "keep": 2,
        "existing_count": existing,
        "retained_count": retained,
        "excess_count": excess,
        "readonly": True,
        "affects_decision": False,
    }


def _build(status="EMPTY", existing=0, retained=0, excess=0):
    return BookDiagnosticsVoiceStatusRetentionBundleBuilder().build(
        inspection=_inspection(existing, retained, excess),
        health=_health(status, existing, retained, excess),
        dashboard_projection=_projection(status, existing, retained, excess),
        dashboard_widget=_widget(status, existing, retained, excess),
    )


def test_rc80_empty_bundle():
    bundle = _build()
    assert bundle.version == "RC80-VOICE-STATUS-RETENTION-BUNDLE"
    assert bundle.health["status"] == "EMPTY"


def test_rc80_within_limit_bundle():
    bundle = _build("WITHIN_LIMIT", 2, 2, 0)
    assert bundle.dashboard_widget["existing_count"] == 2


def test_rc80_over_limit_bundle():
    bundle = _build("OVER_LIMIT", 3, 2, 1)
    assert bundle.dashboard_projection["excess_count"] == 1


def test_rc80_is_readonly_and_neutral():
    bundle = _build()
    assert bundle.readonly is True
    assert bundle.affects_decision is False


def test_rc80_rejects_invalid_source_version():
    inspection = _inspection()
    inspection["version"] = "BAD"
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusRetentionBundleBuilder().build(
            inspection=inspection,
            health=_health("EMPTY"),
            dashboard_projection=_projection("EMPTY"),
            dashboard_widget=_widget("EMPTY"),
        )


def test_rc80_rejects_non_readonly_contract():
    health = _health("EMPTY")
    health["readonly"] = False
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusRetentionBundleBuilder().build(
            inspection=_inspection(), health=health,
            dashboard_projection=_projection("EMPTY"),
            dashboard_widget=_widget("EMPTY"),
        )


def test_rc80_rejects_status_mismatch():
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionBundleBuilder().build(
            inspection=_inspection(1, 1, 0),
            health=_health("WITHIN_LIMIT", 1, 1, 0),
            dashboard_projection=_projection("EMPTY", 1, 1, 0),
            dashboard_widget=_widget("WITHIN_LIMIT", 1, 1, 0),
        )


def test_rc80_rejects_context_mismatch():
    widget = _widget("EMPTY")
    widget["prefix"] = "other"
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionBundleBuilder().build(
            inspection=_inspection(), health=_health("EMPTY"),
            dashboard_projection=_projection("EMPTY"), dashboard_widget=widget,
        )


def test_rc80_rejects_inconsistent_rc70_counts():
    inspection = _inspection(3, 1, 1)
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionBundleBuilder().build(
            inspection=inspection,
            health=_health("OVER_LIMIT", 3, 2, 1),
            dashboard_projection=_projection("OVER_LIMIT", 3, 2, 1),
            dashboard_widget=_widget("OVER_LIMIT", 3, 2, 1),
        )


def test_rc80_rejects_downstream_count_mismatch():
    widget = _widget("OVER_LIMIT", 3, 2, 0)
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionBundleBuilder().build(
            inspection=_inspection(3, 2, 1),
            health=_health("OVER_LIMIT", 3, 2, 1),
            dashboard_projection=_projection("OVER_LIMIT", 3, 2, 1),
            dashboard_widget=widget,
        )
