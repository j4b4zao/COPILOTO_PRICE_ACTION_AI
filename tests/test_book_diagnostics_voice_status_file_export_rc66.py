from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from analysis.replay.book_diagnostics_voice_status_export import VoiceStatusExport
from analysis.replay.book_diagnostics_voice_status_file_export import (
    BookDiagnosticsVoiceStatusFileExporter,
)
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def make_export(status: str = "DISABLED") -> VoiceStatusExport:
    return VoiceStatusExport(
        version="RC64-VOICE-STATUS-EXPORT-CONTRACT",
        schema="copiloto.voice.status.v1",
        generated_at="2026-08-23T12:00:00Z",
        status=status,
        payload={
            "version": "RC62-VOICE-STATUS-BUNDLE",
            "health_report": {"status": status},
            "dashboard_projection": {"status": status},
            "dashboard_widget": {"status": status},
            "readonly": True,
            "affects_decision": False,
        },
    )


def test_rc66_writes_json_atomically(tmp_path):
    target = tmp_path / "voice_status.json"
    result = BookDiagnosticsVoiceStatusFileExporter().write(make_export(), target)
    assert target.exists()
    assert result.path == str(target.resolve())
    assert result.bytes_written == target.stat().st_size


def test_rc66_preserves_status_and_schema(tmp_path):
    target = tmp_path / "voice_status.json"
    result = BookDiagnosticsVoiceStatusFileExporter().write(make_export("READY"), target)
    assert result.status == "READY"
    assert result.schema == "copiloto.voice.status.v1"


def test_rc66_written_file_contains_valid_json(tmp_path):
    target = tmp_path / "voice_status.json"
    BookDiagnosticsVoiceStatusFileExporter().write(make_export(), target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["version"] == "RC64-VOICE-STATUS-EXPORT-CONTRACT"
    assert payload["readonly"] is True


def test_rc66_requires_json_extension(tmp_path):
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusFileExporter().write(make_export(), tmp_path / "voice_status.txt")


def test_rc66_rejects_invalid_source_version(tmp_path):
    payload = make_export().to_dict()
    payload["version"] = "INVALID"
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusFileExporter().write(payload, tmp_path / "voice_status.json")


def test_rc66_rejects_mutable_contract(tmp_path):
    payload = make_export().to_dict()
    payload["readonly"] = False
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceStatusFileExporter().write(payload, tmp_path / "voice_status.json")


def test_rc66_rejects_wrong_schema(tmp_path):
    payload = make_export().to_dict()
    payload["schema"] = "other.schema"
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusFileExporter().write(payload, tmp_path / "voice_status.json")


def test_rc66_service_export_status_file(tmp_path):
    service = BookDiagnosticsVoiceService(enabled=False)
    target = tmp_path / "voice_status.json"
    instant = datetime(2026, 8, 23, 12, 30, tzinfo=timezone.utc)
    result = service.export_status_file(target, generated_at=instant)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert result.version == "RC66-VOICE-STATUS-FILE-EXPORT"
    assert payload["generated_at"] == "2026-08-23T12:30:00Z"


def test_rc66_does_not_initialize_orchestrator(tmp_path):
    service = BookDiagnosticsVoiceService(enabled=False)
    assert service._orchestrator is None
    service.export_status_file(tmp_path / "voice_status.json")
    assert service._orchestrator is None


def test_rc66_result_is_readonly_and_does_not_affect_decision(tmp_path):
    result = BookDiagnosticsVoiceStatusFileExporter().write(
        make_export(), tmp_path / "voice_status.json"
    )
    assert result.readonly is True
    assert result.affects_decision is False
