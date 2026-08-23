from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _service():
    return BookDiagnosticsVoiceService(enabled=False)


def _snapshot(folder: Path, name: str) -> Path:
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_rc79_empty_widget_contract(tmp_path):
    service = _service()
    widget = service.retention_dashboard_widget(tmp_path)
    assert widget.version == "RC78-VOICE-STATUS-RETENTION-DASHBOARD-WIDGET-CONTRACT"
    assert widget.status == "EMPTY"
    assert widget.readonly is True
    assert widget.affects_decision is False


def test_rc79_within_limit(tmp_path):
    _snapshot(tmp_path, "voice_status_001.json")
    _snapshot(tmp_path, "voice_status_002.json")
    widget = _service().retention_dashboard_widget(tmp_path, keep=2)
    assert widget.status == "WITHIN_LIMIT"
    assert widget.existing_count == 2
    assert widget.retained_count == 2
    assert widget.excess_count == 0


def test_rc79_over_limit(tmp_path):
    for index in range(3):
        _snapshot(tmp_path, f"voice_status_{index}.json")
    widget = _service().retention_dashboard_widget(tmp_path, keep=2)
    assert widget.status == "OVER_LIMIT"
    assert widget.existing_count == 3
    assert widget.retained_count == 2
    assert widget.excess_count == 1


def test_rc79_custom_prefix(tmp_path):
    _snapshot(tmp_path, "custom_001.json")
    _snapshot(tmp_path, "voice_status_001.json")
    widget = _service().retention_dashboard_widget(tmp_path, prefix="custom")
    assert widget.prefix == "custom"
    assert widget.existing_count == 1


def test_rc79_missing_directory_is_not_created(tmp_path):
    missing = tmp_path / "missing"
    widget = _service().retention_dashboard_widget(missing)
    assert widget.status == "EMPTY"
    assert widget.directory_exists is False
    assert missing.exists() is False


def test_rc79_does_not_delete_files(tmp_path):
    files = [_snapshot(tmp_path, f"voice_status_{index}.json") for index in range(3)]
    _service().retention_dashboard_widget(tmp_path, keep=1)
    assert all(path.exists() for path in files)


def test_rc79_ignores_unrelated_json(tmp_path):
    _snapshot(tmp_path, "other.json")
    widget = _service().retention_dashboard_widget(tmp_path)
    assert widget.status == "EMPTY"
    assert widget.existing_count == 0


def test_rc79_invalid_keep_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_dashboard_widget(tmp_path, keep=0)


def test_rc79_invalid_prefix_rejected(tmp_path):
    with pytest.raises(ValueError):
        _service().retention_dashboard_widget(tmp_path, prefix="bad/prefix")


def test_rc79_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.retention_dashboard_widget(tmp_path)
    assert service._orchestrator is None
