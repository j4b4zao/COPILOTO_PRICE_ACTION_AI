from datetime import datetime, timezone
import json

import pytest

from analysis.replay.book_diagnostics_voice_status_export import BookDiagnosticsVoiceStatusExporter


def _bundle(status="DISABLED"):
    return {
        "version": "RC62-VOICE-STATUS-BUNDLE",
        "health_report": {"status": status},
        "dashboard_projection": {"status": status},
        "dashboard_widget": {"status": status},
        "readonly": True,
        "affects_decision": False,
    }


def test_rc64_exports_versioned_envelope():
    result = BookDiagnosticsVoiceStatusExporter().export(_bundle())
    assert result.version == "RC64-VOICE-STATUS-EXPORT-CONTRACT"
    assert result.schema == "copiloto.voice.status.v1"


def test_rc64_preserves_bundle_payload():
    source = _bundle("READY")
    result = BookDiagnosticsVoiceStatusExporter().export(source)
    assert result.payload == source
    assert result.status == "READY"


def test_rc64_is_readonly_and_does_not_affect_decision():
    result = BookDiagnosticsVoiceStatusExporter().export(_bundle())
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc64_uses_stable_utc_timestamp():
    instant = datetime(2026, 8, 23, 12, 30, tzinfo=timezone.utc)
    result = BookDiagnosticsVoiceStatusExporter().export(_bundle(), generated_at=instant)
    assert result.generated_at == "2026-08-23T12:30:00Z"


def test_rc64_accepts_naive_timestamp_as_utc():
    instant = datetime(2026, 8, 23, 12, 30)
    result = BookDiagnosticsVoiceStatusExporter().export(_bundle(), generated_at=instant)
    assert result.generated_at == "2026-08-23T12:30:00Z"


def test_rc64_to_json_is_valid_and_contains_schema():
    result = BookDiagnosticsVoiceStatusExporter().export(_bundle())
    payload = json.loads(result.to_json())
    assert payload["schema"] == "copiloto.voice.status.v1"
    assert payload["payload"]["version"] == "RC62-VOICE-STATUS-BUNDLE"


def test_rc64_rejects_wrong_source_version():
    source = _bundle()
    source["version"] = "WRONG"
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusExporter().export(source)


def test_rc64_rejects_non_readonly_bundle():
    source = _bundle()
    source["readonly"] = False
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusExporter().export(source)


def test_rc64_rejects_decision_affecting_bundle():
    source = _bundle()
    source["affects_decision"] = True
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusExporter().export(source)


def test_rc64_rejects_inconsistent_status_payloads():
    source = _bundle("READY")
    source["dashboard_widget"]["status"] = "DEGRADED"
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusExporter().export(source)
