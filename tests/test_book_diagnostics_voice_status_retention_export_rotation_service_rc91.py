from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def _system():
    return SystemInitializer(
        voice_config=VoiceConfig(enabled=False, backend="NULL_TTS")
    ).inicializar()


def test_rc91_exposes_inspection_through_system_voice(tmp_path):
    system = _system()
    result = system.voice.inspect_retention_status_exports(tmp_path)
    assert result.version == "RC90-VOICE-STATUS-RETENTION-EXPORT-ROTATION-INSPECTION"
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc91_missing_directory_is_not_created(tmp_path):
    system = _system()
    target = tmp_path / "missing"
    result = system.voice.inspect_retention_status_exports(target)
    assert result.directory_exists is False
    assert not target.exists()


def test_rc91_filters_only_retention_export_series(tmp_path):
    system = _system()
    (tmp_path / "voice_retention_status_001.json").write_text("{}", encoding="utf-8")
    (tmp_path / "voice_status_001.json").write_text("{}", encoding="utf-8")
    (tmp_path / "other.json").write_text("{}", encoding="utf-8")
    result = system.voice.inspect_retention_status_exports(tmp_path)
    assert len(result.existing_files) == 1
    assert Path(result.existing_files[0]).name == "voice_retention_status_001.json"


def test_rc91_calculates_would_remove_without_deleting(tmp_path):
    system = _system()
    for index in range(3):
        (tmp_path / f"voice_retention_status_{index:03d}.json").write_text("{}", encoding="utf-8")
    result = system.voice.inspect_retention_status_exports(tmp_path, export_keep=2)
    assert len(result.retained_files) == 2
    assert len(result.would_remove_files) == 1
    assert len(list(tmp_path.glob("voice_retention_status_*.json"))) == 3


def test_rc91_supports_custom_prefix(tmp_path):
    system = _system()
    (tmp_path / "retention_audit_001.json").write_text("{}", encoding="utf-8")
    result = system.voice.inspect_retention_status_exports(
        tmp_path,
        export_prefix="retention_audit",
    )
    assert result.export_prefix == "retention_audit"
    assert len(result.existing_files) == 1


def test_rc91_rejects_export_keep_below_one(tmp_path):
    system = _system()
    with pytest.raises(ValueError):
        system.voice.inspect_retention_status_exports(tmp_path, export_keep=0)


def test_rc91_rejects_unsafe_prefix(tmp_path):
    system = _system()
    with pytest.raises(ValueError):
        system.voice.inspect_retention_status_exports(tmp_path, export_prefix="bad/prefix")


def test_rc91_does_not_initialize_orchestrator(tmp_path):
    system = _system()
    assert system.voice._orchestrator is None
    system.voice.inspect_retention_status_exports(tmp_path)
    assert system.voice._orchestrator is None


def test_rc91_does_not_create_any_files(tmp_path):
    system = _system()
    before = set(tmp_path.iterdir())
    system.voice.inspect_retention_status_exports(tmp_path)
    after = set(tmp_path.iterdir())
    assert before == after


def test_rc91_voice_remains_disabled(tmp_path):
    system = _system()
    system.voice.inspect_retention_status_exports(tmp_path)
    assert system.voice.enabled is False
    assert system.voice.available is False
