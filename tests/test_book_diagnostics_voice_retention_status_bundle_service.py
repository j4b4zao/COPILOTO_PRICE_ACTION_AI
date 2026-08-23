from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _service():
    return BookDiagnosticsVoiceService(enabled=False)


def _snapshot(folder: Path, name: str) -> Path:
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_rc81_empty_bundle_contract(tmp_path):
    bundle = _service().retention_status_bundle(tmp_path)
    assert bundle.version == "RC80-VOICE-STATUS-RETENTION-BUNDLE"
    assert bundle.health["status"] == "EMPTY"
    assert bundle.dashboard_projection["status"] == "EMPTY"
    assert bundle.dashboard_widget["status"] == "EMPTY"
    assert bundle.readonly is True
    assert bundle.affects_decision is False


def test_rc81_within_limit(tmp_path):
    _snapshot(tmp_path, "voice_status_001.json")
    _snapshot(tmp_path, "voice_status_002.json")
    bundle = _service().retention_status_bundle(tmp_path, keep=2)
    assert bundle.health["status"] == "WITHIN_LIMIT"
    assert bundle.health["existing_count"] == 2
    assert bundle.dashboard_projection["retained_count"] == 2
    assert bundle.dashboard_widget["excess_count"] == 0


def test_rc81_over_limit(tmp_path):
    for index in range(3):
        _snapshot(tmp_path, f"voice_status_{index}.json")
    bundle = _service().retention_status_bundle(tmp_path, keep=2)
    assert bundle.health["status"] == "OVER_LIMIT"
    assert bundle.health["existing_count"] == 3
    assert bundle.health["would_remove_count"] == 1
    assert bundle.dashboard_widget["excess_count"] == 1


def test_rc81_custom_prefix(tmp_path):
    _snapshot(tmp_path, "custom_001.json")
    _snapshot(tmp_path, "voice_status_001.json")
    bundle = _service().retention_status_bundle(tmp_path, prefix="custom")
    assert bundle.inspection["prefix"] == "custom"
    assert bundle.health["existing_count"] == 1


def test_rc81_missing_directory_is_not_created(tmp_path):
    missing = tmp_path / "missing"
    bundle = _service().retention_status_bundle(missing)
    assert bundle.health["status"] == "EMPTY"
    assert bundle.inspection["directory_exists"] is False
    assert missing.exists() is False


def test_rc81_does_not_delete_files(tmp_path):
    files = [_snapshot(tmp_path, f"voice_status_{index}.json") for index in range(3)]
    _service().retention_status_bundle(tmp_path, keep=1)
    assert all(path.exists() for path in files)


def test_rc81_ignores_unrelated_json(tmp_path):
    _snapshot(tmp_path, "other.json")
    bundle = _service().retention_status_bundle(tmp_path)
    assert bundle.health["status"] == "EMPTY"
    assert bundle.health["existing_count"] == 0


def test_rc81_invalid_keep_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_bundle(tmp_path, keep=0)


def test_rc81_invalid_prefix_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_status_bundle(tmp_path, prefix="bad/prefix")


def test_rc81_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.retention_status_bundle(tmp_path)
    assert service._orchestrator is None
