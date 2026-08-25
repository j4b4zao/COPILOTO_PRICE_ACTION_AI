from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _service():
    return BookDiagnosticsVoiceService(enabled=False)


def _snapshot(folder: Path, name: str) -> Path:
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_rc84_empty_export_contract(tmp_path):
    export = _service().retention_status_export(tmp_path)
    assert export.version == "RC83-VOICE-STATUS-RETENTION-EXPORT-CONTRACT"
    assert export.schema == "copiloto.voice.status.retention.v1"
    assert export.status == "EMPTY"
    assert export.readonly is True
    assert export.affects_decision is False


def test_rc84_within_limit(tmp_path):
    _snapshot(tmp_path, "voice_status_001.json")
    export = _service().retention_status_export(tmp_path, keep=2)
    assert export.status == "WITHIN_LIMIT"
    assert export.payload["health"]["existing_count"] == 1


def test_rc84_over_limit(tmp_path):
    for index in range(3):
        _snapshot(tmp_path, f"voice_status_{index}.json")
    export = _service().retention_status_export(tmp_path, keep=2)
    assert export.status == "OVER_LIMIT"
    assert export.payload["health"]["would_remove_count"] == 1


def test_rc84_custom_prefix(tmp_path):
    _snapshot(tmp_path, "custom_001.json")
    _snapshot(tmp_path, "voice_status_001.json")
    export = _service().retention_status_export(tmp_path, prefix="custom")
    assert export.payload["inspection"]["prefix"] == "custom"
    assert export.payload["health"]["existing_count"] == 1


def test_rc84_generated_at_is_preserved_in_utc(tmp_path):
    instant = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    export = _service().retention_status_export(tmp_path, generated_at=instant)
    assert export.generated_at == "2026-08-23T12:00:00Z"


def test_rc84_missing_directory_is_not_created(tmp_path):
    missing = tmp_path / "missing"
    export = _service().retention_status_export(missing)
    assert export.status == "EMPTY"
    assert export.payload["inspection"]["directory_exists"] is False
    assert missing.exists() is False


def test_rc84_does_not_delete_files(tmp_path):
    files = [_snapshot(tmp_path, f"voice_status_{index}.json") for index in range(3)]
    _service().retention_status_export(tmp_path, keep=1)
    assert all(path.exists() for path in files)


def test_rc84_invalid_keep_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_export(tmp_path, keep=0)


def test_rc84_invalid_prefix_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_export(tmp_path, prefix="bad/prefix")


def test_rc84_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.retention_status_export(tmp_path)
    assert service._orchestrator is None
