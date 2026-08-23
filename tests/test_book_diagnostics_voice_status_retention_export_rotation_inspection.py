from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_inspection import (
    BookDiagnosticsVoiceStatusRetentionExportRotationInspector,
)


def _inspector():
    return BookDiagnosticsVoiceStatusRetentionExportRotationInspector()


def _touch(path: Path, content="{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_rc90_reports_missing_directory_without_creating_it(tmp_path):
    folder = tmp_path / "missing"
    result = _inspector().inspect(folder)
    assert result.version == "RC90-VOICE-STATUS-RETENTION-EXPORT-ROTATION-INSPECTION"
    assert result.directory_exists is False
    assert result.existing_files == ()
    assert not folder.exists()


def test_rc90_lists_only_matching_history_files(tmp_path):
    folder = tmp_path / "history"
    _touch(folder / "voice_retention_status_001.json")
    _touch(folder / "voice_retention_status_002.json")
    _touch(folder / "voice_status_001.json")
    _touch(folder / "other.json")
    result = _inspector().inspect(folder)
    names = {Path(path).name for path in result.existing_files}
    assert names == {"voice_retention_status_001.json", "voice_retention_status_002.json"}


def test_rc90_respects_export_keep(tmp_path):
    folder = tmp_path / "history"
    for index in range(4):
        _touch(folder / f"voice_retention_status_{index:03d}.json")
    result = _inspector().inspect(folder, export_keep=2)
    assert len(result.existing_files) == 4
    assert len(result.retained_files) == 2
    assert len(result.would_remove_files) == 2


def test_rc90_does_not_delete_files(tmp_path):
    folder = tmp_path / "history"
    files = [_touch(folder / f"voice_retention_status_{index:03d}.json") for index in range(3)]
    result = _inspector().inspect(folder, export_keep=1)
    assert len(result.would_remove_files) == 2
    assert all(path.exists() for path in files)


def test_rc90_preserves_unrelated_jsons(tmp_path):
    folder = tmp_path / "history"
    unrelated = _touch(folder / "unrelated.json")
    _touch(folder / "voice_retention_status_001.json")
    _inspector().inspect(folder, export_keep=1)
    assert unrelated.exists()


def test_rc90_supports_custom_prefix(tmp_path):
    folder = tmp_path / "history"
    _touch(folder / "retention_audit_001.json")
    result = _inspector().inspect(folder, export_prefix="retention_audit")
    assert result.export_prefix == "retention_audit"
    assert len(result.existing_files) == 1


def test_rc90_rejects_export_keep_below_one(tmp_path):
    with pytest.raises(ValueError):
        _inspector().inspect(tmp_path / "history", export_keep=0)


def test_rc90_rejects_empty_prefix(tmp_path):
    with pytest.raises(ValueError):
        _inspector().inspect(tmp_path / "history", export_prefix="")


def test_rc90_rejects_unsafe_prefix(tmp_path):
    with pytest.raises(ValueError):
        _inspector().inspect(tmp_path / "history", export_prefix="bad/prefix")


def test_rc90_contract_is_readonly_and_neutral(tmp_path):
    result = _inspector().inspect(tmp_path / "history")
    assert result.readonly is True
    assert result.affects_decision is False
