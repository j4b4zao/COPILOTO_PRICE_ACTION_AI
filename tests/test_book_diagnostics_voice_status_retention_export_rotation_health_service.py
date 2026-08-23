from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service_rc94 import BookDiagnosticsVoiceServiceRC94
from core.system_initializer import SystemInitializer


def _service():
    return BookDiagnosticsVoiceServiceRC94(config=VoiceConfig(enabled=False, backend="NULL_TTS"))


def _touch_series(folder: Path, count: int, prefix: str = "voice_retention_status"):
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        path = folder / f"{prefix}_{index:03d}.json"
        path.write_text("{}", encoding="utf-8")
        path.touch()


def test_rc94_empty_status_for_missing_directory(tmp_path):
    folder = tmp_path / "missing"
    result = _service().retention_status_exports_health(folder)
    assert result.status == "EMPTY"
    assert result.directory_exists is False
    assert not folder.exists()


def test_rc94_empty_status_for_existing_empty_directory(tmp_path):
    folder = tmp_path / "history"
    folder.mkdir()
    result = _service().retention_status_exports_health(folder)
    assert result.status == "EMPTY"
    assert result.existing_count == 0


def test_rc94_within_limit_status(tmp_path):
    folder = tmp_path / "history"
    _touch_series(folder, 2)
    result = _service().retention_status_exports_health(folder, export_keep=3)
    assert result.status == "WITHIN_LIMIT"
    assert result.existing_count == 2
    assert result.would_remove_count == 0


def test_rc94_over_limit_status(tmp_path):
    folder = tmp_path / "history"
    _touch_series(folder, 3)
    result = _service().retention_status_exports_health(folder, export_keep=2)
    assert result.status == "OVER_LIMIT"
    assert result.retained_count == 2
    assert result.would_remove_count == 1


def test_rc94_preserves_custom_prefix(tmp_path):
    folder = tmp_path / "history"
    _touch_series(folder, 1, prefix="retention_audit")
    result = _service().retention_status_exports_health(
        folder,
        export_keep=4,
        export_prefix="retention_audit",
    )
    assert result.export_prefix == "retention_audit"
    assert result.export_keep == 4


def test_rc94_does_not_delete_files(tmp_path):
    folder = tmp_path / "history"
    _touch_series(folder, 3)
    before = sorted(path.name for path in folder.iterdir())
    result = _service().retention_status_exports_health(folder, export_keep=1)
    after = sorted(path.name for path in folder.iterdir())
    assert result.status == "OVER_LIMIT"
    assert after == before


def test_rc94_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.retention_status_exports_health(tmp_path / "missing")
    assert service._orchestrator is None


def test_rc94_rejects_invalid_keep(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_exports_health(tmp_path / "history", export_keep=0)


def test_rc94_rejects_unsafe_prefix(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_exports_health(
            tmp_path / "history",
            export_prefix="bad/prefix",
        )


def test_rc94_is_exposed_by_system_initializer():
    system = SystemInitializer(
        voice_config=VoiceConfig(enabled=False, backend="NULL_TTS")
    ).inicializar()
    assert isinstance(system.voice, BookDiagnosticsVoiceServiceRC94)
    assert system.voice.enabled is False
    assert hasattr(system.voice, "retention_status_exports_health")
