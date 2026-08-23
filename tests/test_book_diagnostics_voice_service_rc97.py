from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service_rc97 import BookDiagnosticsVoiceServiceRC97


def _service():
    return BookDiagnosticsVoiceServiceRC97(config=VoiceConfig(enabled=False, backend="NULL_TTS"))


def _touch(folder: Path, name: str):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_rc97_empty_projection_for_missing_directory(tmp_path):
    folder = tmp_path / "missing"
    service = _service()
    result = service.retention_status_exports_dashboard_projection(folder)
    assert result.version == "RC96-VOICE-STATUS-RETENTION-EXPORT-ROTATION-DASHBOARD-PROJECTION"
    assert result.status == "EMPTY"
    assert result.readonly is True
    assert result.affects_decision is False
    assert not folder.exists()


def test_rc97_within_limit_projection(tmp_path):
    folder = tmp_path / "history"
    _touch(folder, "voice_retention_status_001.json")
    _touch(folder, "voice_retention_status_002.json")
    result = _service().retention_status_exports_dashboard_projection(folder, export_keep=2)
    assert result.status == "WITHIN_LIMIT"
    assert result.existing_count == 2
    assert result.retained_count == 2
    assert result.excess_count == 0


def test_rc97_over_limit_projection(tmp_path):
    folder = tmp_path / "history"
    for index in range(3):
        _touch(folder, f"voice_retention_status_{index}.json")
    result = _service().retention_status_exports_dashboard_projection(folder, export_keep=2)
    assert result.status == "OVER_LIMIT"
    assert result.existing_count == 3
    assert result.retained_count == 2
    assert result.excess_count == 1


def test_rc97_custom_prefix(tmp_path):
    folder = tmp_path / "history"
    _touch(folder, "retention_audit_001.json")
    result = _service().retention_status_exports_dashboard_projection(
        folder,
        export_keep=5,
        export_prefix="retention_audit",
    )
    assert result.export_prefix == "retention_audit"
    assert result.existing_count == 1


def test_rc97_ignores_unrelated_json(tmp_path):
    folder = tmp_path / "history"
    _touch(folder, "voice_retention_status_001.json")
    unrelated = _touch(folder, "other.json")
    result = _service().retention_status_exports_dashboard_projection(folder)
    assert result.existing_count == 1
    assert unrelated.exists()


def test_rc97_does_not_delete_files(tmp_path):
    folder = tmp_path / "history"
    files = [_touch(folder, f"voice_retention_status_{index}.json") for index in range(3)]
    _service().retention_status_exports_dashboard_projection(folder, export_keep=1)
    assert all(path.exists() for path in files)


def test_rc97_rejects_export_keep_below_one(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_exports_dashboard_projection(tmp_path, export_keep=0)


def test_rc97_rejects_unsafe_prefix(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_exports_dashboard_projection(tmp_path, export_prefix="bad/prefix")


def test_rc97_voice_remains_disabled_and_orchestrator_uninitialized(tmp_path):
    service = _service()
    service.retention_status_exports_dashboard_projection(tmp_path)
    assert service.enabled is False
    assert service._orchestrator is None


def test_rc97_projection_preserves_context(tmp_path):
    folder = tmp_path / "history"
    result = _service().retention_status_exports_dashboard_projection(
        folder,
        export_keep=7,
        export_prefix="voice_retention_status",
    )
    assert result.export_directory == str(folder.resolve())
    assert result.export_keep == 7
    assert result.directory_exists is False
