from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def make_service():
    return BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False, backend="NULL_TTS"))


def touch(path: Path, name: str):
    file = path / name
    file.write_text("{}", encoding="utf-8")
    return file


def test_rc77_empty_projection(tmp_path):
    result = make_service().retention_dashboard_projection(tmp_path, keep=20)
    assert result.version == "RC76-VOICE-STATUS-RETENTION-DASHBOARD-PROJECTION"
    assert result.status == "EMPTY"
    assert result.existing_count == 0
    assert result.excess_count == 0


def test_rc77_missing_directory_not_created(tmp_path):
    target = tmp_path / "missing"
    result = make_service().retention_dashboard_projection(target)
    assert result.status == "EMPTY"
    assert result.directory_exists is False
    assert not target.exists()


def test_rc77_within_limit(tmp_path):
    touch(tmp_path, "voice_status_001.json")
    touch(tmp_path, "voice_status_002.json")
    result = make_service().retention_dashboard_projection(tmp_path, keep=2)
    assert result.status == "WITHIN_LIMIT"
    assert result.existing_count == 2
    assert result.retained_count == 2
    assert result.excess_count == 0


def test_rc77_over_limit(tmp_path):
    for index in range(3):
        touch(tmp_path, f"voice_status_{index}.json")
    result = make_service().retention_dashboard_projection(tmp_path, keep=2)
    assert result.status == "OVER_LIMIT"
    assert result.existing_count == 3
    assert result.retained_count == 2
    assert result.excess_count == 1


def test_rc77_custom_prefix(tmp_path):
    touch(tmp_path, "custom_001.json")
    touch(tmp_path, "voice_status_001.json")
    result = make_service().retention_dashboard_projection(tmp_path, prefix="custom")
    assert result.prefix == "custom"
    assert result.existing_count == 1


def test_rc77_readonly_contract(tmp_path):
    result = make_service().retention_dashboard_projection(tmp_path)
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc77_does_not_delete_files(tmp_path):
    files = [touch(tmp_path, f"voice_status_{index}.json") for index in range(3)]
    make_service().retention_dashboard_projection(tmp_path, keep=1)
    assert all(file.exists() for file in files)


def test_rc77_does_not_initialize_orchestrator(tmp_path):
    service = make_service()
    assert service._orchestrator is None
    service.retention_dashboard_projection(tmp_path)
    assert service._orchestrator is None


def test_rc77_invalid_keep_rejected(tmp_path):
    with pytest.raises(ValueError):
        make_service().retention_dashboard_projection(tmp_path, keep=0)


def test_rc77_invalid_prefix_rejected(tmp_path):
    with pytest.raises(ValueError):
        make_service().retention_dashboard_projection(tmp_path, prefix="bad/prefix")
