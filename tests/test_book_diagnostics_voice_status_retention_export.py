from datetime import datetime, timezone

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_export import (
    BookDiagnosticsVoiceStatusRetentionExporter,
)


def _bundle(status="EMPTY"):
    return {
        "version": "RC80-VOICE-STATUS-RETENTION-BUNDLE",
        "inspection": {
            "version": "RC70-VOICE-STATUS-RETENTION-INSPECTION",
            "directory": "logs/voice",
            "directory_exists": False,
            "prefix": "voice_status",
            "keep": 20,
            "existing_files": [],
            "retained_files": [],
            "would_remove_files": [],
            "readonly": True,
            "affects_decision": False,
        },
        "health": {
            "version": "RC73-VOICE-STATUS-RETENTION-HEALTH",
            "status": status,
            "summary": "ok",
            "directory": "logs/voice",
            "directory_exists": False,
            "prefix": "voice_status",
            "keep": 20,
            "existing_count": 0,
            "retained_count": 0,
            "would_remove_count": 0,
            "readonly": True,
            "affects_decision": False,
        },
        "dashboard_projection": {
            "version": "RC76-VOICE-STATUS-RETENTION-DASHBOARD-PROJECTION",
            "status": status,
            "label": "x",
            "summary": "ok",
            "directory": "logs/voice",
            "directory_exists": False,
            "prefix": "voice_status",
            "keep": 20,
            "existing_count": 0,
            "retained_count": 0,
            "excess_count": 0,
            "readonly": True,
            "affects_decision": False,
        },
        "dashboard_widget": {
            "version": "RC78-VOICE-STATUS-RETENTION-DASHBOARD-WIDGET-CONTRACT",
            "title": "Voice Status Retention",
            "status": status,
            "label": "x",
            "detail": "ok",
            "directory": "logs/voice",
            "directory_exists": False,
            "prefix": "voice_status",
            "keep": 20,
            "existing_count": 0,
            "retained_count": 0,
            "excess_count": 0,
            "readonly": True,
            "affects_decision": False,
        },
        "readonly": True,
        "affects_decision": False,
    }


def test_rc83_schema_and_version():
    result = BookDiagnosticsVoiceStatusRetentionExporter().export(_bundle())
    assert result.version == "RC83-VOICE-STATUS-RETENTION-EXPORT-CONTRACT"
    assert result.schema == "copiloto.voice.status.retention.v1"


def test_rc83_preserves_payload():
    bundle = _bundle("WITHIN_LIMIT")
    result = BookDiagnosticsVoiceStatusRetentionExporter().export(bundle)
    assert result.payload == bundle
    assert result.status == "WITHIN_LIMIT"


def test_rc83_generated_at_is_utc_z():
    instant = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    result = BookDiagnosticsVoiceStatusRetentionExporter().export(_bundle(), generated_at=instant)
    assert result.generated_at == "2026-08-23T12:00:00Z"


def test_rc83_naive_datetime_assumed_utc():
    instant = datetime(2026, 8, 23, 12, 0)
    result = BookDiagnosticsVoiceStatusRetentionExporter().export(_bundle(), generated_at=instant)
    assert result.generated_at == "2026-08-23T12:00:00Z"


def test_rc83_json_is_valid_and_contains_schema():
    text = BookDiagnosticsVoiceStatusRetentionExporter().export(_bundle()).to_json()
    assert '"copiloto.voice.status.retention.v1"' in text
    assert '"RC80-VOICE-STATUS-RETENTION-BUNDLE"' in text


def test_rc83_readonly_contract():
    result = BookDiagnosticsVoiceStatusRetentionExporter().export(_bundle())
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc83_rejects_wrong_source_version():
    bundle = _bundle()
    bundle["version"] = "WRONG"
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusRetentionExporter().export(bundle)


def test_rc83_rejects_non_readonly_bundle():
    bundle = _bundle()
    bundle["readonly"] = False
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusRetentionExporter().export(bundle)


def test_rc83_rejects_status_mismatch():
    bundle = _bundle("EMPTY")
    bundle["dashboard_widget"]["status"] = "OVER_LIMIT"
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionExporter().export(bundle)


def test_rc83_rejects_invalid_status():
    bundle = _bundle("BROKEN")
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionExporter().export(bundle)
