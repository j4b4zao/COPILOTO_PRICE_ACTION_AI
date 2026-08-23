from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def test_inspection_returns_rc70_contract(tmp_path):
    service = BookDiagnosticsVoiceService(enabled=False)
    result = service.inspect_status_retention(tmp_path)
    assert result.version == "RC70-VOICE-STATUS-RETENTION-INSPECTION"
    assert result.readonly is True
    assert result.affects_decision is False


def test_missing_directory_is_not_created(tmp_path):
    target = tmp_path / "missing"
    service = BookDiagnosticsVoiceService(enabled=False)
    result = service.inspect_status_retention(target)
    assert result.directory_exists is False
    assert target.exists() is False


def test_existing_files_are_reported(tmp_path):
    (tmp_path / "voice_status_a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "voice_status_b.json").write_text("{}", encoding="utf-8")
    service = BookDiagnosticsVoiceService(enabled=False)
    result = service.inspect_status_retention(tmp_path, keep=20)
    assert len(result.existing_files) == 2


def test_keep_is_forwarded(tmp_path):
    for index in range(3):
        (tmp_path / f"voice_status_{index}.json").write_text("{}", encoding="utf-8")
    service = BookDiagnosticsVoiceService(enabled=False)
    result = service.inspect_status_retention(tmp_path, keep=1)
    assert result.keep == 1
    assert len(result.retained_files) == 1
    assert len(result.would_remove_files) == 2


def test_custom_prefix_is_forwarded(tmp_path):
    (tmp_path / "custom_a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "voice_status_a.json").write_text("{}", encoding="utf-8")
    service = BookDiagnosticsVoiceService(enabled=False)
    result = service.inspect_status_retention(tmp_path, prefix="custom")
    assert result.prefix == "custom"
    assert len(result.existing_files) == 1
    assert Path(result.existing_files[0]).name == "custom_a.json"


def test_inspection_does_not_delete_files(tmp_path):
    for index in range(3):
        (tmp_path / f"voice_status_{index}.json").write_text("{}", encoding="utf-8")
    service = BookDiagnosticsVoiceService(enabled=False)
    service.inspect_status_retention(tmp_path, keep=1)
    assert len(list(tmp_path.glob("voice_status_*.json"))) == 3


def test_inspection_does_not_initialize_orchestrator(tmp_path):
    service = BookDiagnosticsVoiceService(enabled=False)
    assert service._orchestrator is None
    service.inspect_status_retention(tmp_path)
    assert service._orchestrator is None


def test_invalid_keep_is_rejected(tmp_path):
    service = BookDiagnosticsVoiceService(enabled=False)
    with pytest.raises(ValueError):
        service.inspect_status_retention(tmp_path, keep=0)


def test_invalid_prefix_is_rejected(tmp_path):
    service = BookDiagnosticsVoiceService(enabled=False)
    with pytest.raises(ValueError):
        service.inspect_status_retention(tmp_path, prefix="bad prefix")


def test_inspection_does_not_require_voice_enabled(tmp_path):
    service = BookDiagnosticsVoiceService(enabled=False)
    result = service.inspect_status_retention(tmp_path)
    assert result.readonly is True
