import json
from datetime import datetime, timezone

import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _service():
    return BookDiagnosticsVoiceService(enabled=False)


def _snapshot(folder, name="voice_status_001.json"):
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_rc85_exports_empty_status_to_json_file(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "out" / "retention.json"
    result = _service().export_retention_status_file(source, destination)
    assert result.version == "RC85-VOICE-STATUS-RETENTION-FILE-EXPORT"
    assert result.status == "EMPTY"
    assert result.schema == "copiloto.voice.status.retention.v1"
    assert destination.exists()


def test_rc85_exports_within_limit_status(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    _snapshot(source)
    destination = tmp_path / "retention.json"
    result = _service().export_retention_status_file(source, destination, keep=2)
    assert result.status == "WITHIN_LIMIT"


def test_rc85_exports_over_limit_status_without_deleting_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    files = [_snapshot(source, f"voice_status_{index}.json") for index in range(3)]
    destination = tmp_path / "retention.json"
    result = _service().export_retention_status_file(source, destination, keep=1)
    assert result.status == "OVER_LIMIT"
    assert all(path.exists() for path in files)


def test_rc85_writes_valid_rc83_payload(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "retention.json"
    _service().export_retention_status_file(source, destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["version"] == "RC83-VOICE-STATUS-RETENTION-EXPORT-CONTRACT"
    assert payload["schema"] == "copiloto.voice.status.retention.v1"
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_rc85_supports_injected_timestamp(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "retention.json"
    instant = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    _service().export_retention_status_file(source, destination, generated_at=instant)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["generated_at"] == "2026-08-23T12:00:00Z"


def test_rc85_requires_json_extension(tmp_path):
    with pytest.raises(ValueError):
        _service().export_retention_status_file(tmp_path / "source", tmp_path / "retention.txt")


def test_rc85_custom_prefix_is_preserved(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    _snapshot(source, "custom_001.json")
    destination = tmp_path / "retention.json"
    _service().export_retention_status_file(source, destination, prefix="custom")
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["payload"]["inspection"]["prefix"] == "custom"


def test_rc85_invalid_keep_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().export_retention_status_file(tmp_path / "source", tmp_path / "retention.json", keep=0)


def test_rc85_invalid_prefix_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().export_retention_status_file(tmp_path / "source", tmp_path / "retention.json", prefix="bad/prefix")


def test_rc85_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.export_retention_status_file(tmp_path / "source", tmp_path / "retention.json")
    assert service._orchestrator is None
