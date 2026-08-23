from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _service():
    return BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False, backend="NULL_TTS"))


def test_retention_health_returns_rc73_contract_for_missing_directory(tmp_path):
    target = tmp_path / "missing"
    result = _service().retention_health(target)
    assert result.version == "RC73-VOICE-STATUS-RETENTION-HEALTH"
    assert result.status == "EMPTY"
    assert result.readonly is True
    assert result.affects_decision is False
    assert target.exists() is False


def test_retention_health_within_limit(tmp_path):
    for index in range(2):
        (tmp_path / f"voice_status_{index}.json").write_text("{}", encoding="utf-8")
    result = _service().retention_health(tmp_path, keep=3)
    assert result.status == "WITHIN_LIMIT"
    assert result.existing_count == 2
    assert result.retained_count == 2
    assert result.excess_count == 0


def test_retention_health_over_limit(tmp_path):
    for index in range(4):
        (tmp_path / f"voice_status_{index}.json").write_text("{}", encoding="utf-8")
    result = _service().retention_health(tmp_path, keep=2)
    assert result.status == "OVER_LIMIT"
    assert result.existing_count == 4
    assert result.retained_count == 2
    assert result.excess_count == 2


def test_retention_health_preserves_prefix(tmp_path):
    (tmp_path / "custom_1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "voice_status_1.json").write_text("{}", encoding="utf-8")
    result = _service().retention_health(tmp_path, keep=5, prefix="custom")
    assert result.prefix == "custom"
    assert result.existing_count == 1


def test_retention_health_rejects_invalid_keep(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_health(tmp_path, keep=0)


def test_retention_health_rejects_invalid_prefix(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_health(tmp_path, prefix="bad prefix")


def test_retention_health_does_not_delete_files(tmp_path):
    files = []
    for index in range(3):
        path = tmp_path / f"voice_status_{index}.json"
        path.write_text("{}", encoding="utf-8")
        files.append(path)
    _service().retention_health(tmp_path, keep=1)
    assert all(path.exists() for path in files)


def test_retention_health_does_not_create_snapshot(tmp_path):
    before = set(tmp_path.iterdir())
    _service().retention_health(tmp_path, keep=2)
    after = set(tmp_path.iterdir())
    assert before == after


def test_retention_health_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.retention_health(tmp_path)
    assert service._orchestrator is None


def test_retention_health_works_with_voice_disabled(tmp_path):
    service = _service()
    assert service.enabled is False
    result = service.retention_health(tmp_path)
    assert result.status == "EMPTY"
