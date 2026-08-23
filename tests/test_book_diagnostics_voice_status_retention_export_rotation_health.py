from dataclasses import replace

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_health import (
    BookDiagnosticsVoiceStatusRetentionExportRotationHealthReporter,
)
from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_inspection import (
    VoiceStatusRetentionExportRotationInspection,
)


def _inspection(*, existing=(), retained=(), would_remove=(), directory_exists=True, export_keep=20):
    return VoiceStatusRetentionExportRotationInspection(
        version="RC90-VOICE-STATUS-RETENTION-EXPORT-ROTATION-INSPECTION",
        export_directory="/tmp/history",
        export_prefix="voice_retention_status",
        export_keep=export_keep,
        directory_exists=directory_exists,
        existing_files=tuple(existing),
        retained_files=tuple(retained),
        would_remove_files=tuple(would_remove),
    )


def _reporter():
    return BookDiagnosticsVoiceStatusRetentionExportRotationHealthReporter()


def test_rc93_empty_when_no_history_files():
    result = _reporter().build(_inspection(directory_exists=False))
    assert result.status == "EMPTY"
    assert result.existing_count == 0
    assert result.retained_count == 0
    assert result.would_remove_count == 0


def test_rc93_within_limit_when_all_files_retained():
    files = ("a.json", "b.json")
    result = _reporter().build(_inspection(existing=files, retained=files, export_keep=2))
    assert result.status == "WITHIN_LIMIT"
    assert result.existing_count == 2
    assert result.retained_count == 2
    assert result.would_remove_count == 0


def test_rc93_over_limit_when_files_would_be_removed():
    result = _reporter().build(
        _inspection(existing=("a", "b", "c"), retained=("a", "b"), would_remove=("c",), export_keep=2)
    )
    assert result.status == "OVER_LIMIT"
    assert result.would_remove_count == 1


def test_rc93_preserves_export_context():
    result = _reporter().build(_inspection())
    assert result.export_directory == "/tmp/history"
    assert result.export_prefix == "voice_retention_status"
    assert result.export_keep == 20


def test_rc93_is_readonly_and_does_not_affect_decision():
    result = _reporter().build(_inspection())
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc93_rejects_wrong_source_version():
    inspection = replace(_inspection(), version="RC89")
    with pytest.raises(PermissionError):
        _reporter().build(inspection)


def test_rc93_rejects_non_readonly_source():
    inspection = replace(_inspection(), readonly=False)
    with pytest.raises(PermissionError):
        _reporter().build(inspection)


def test_rc93_rejects_affects_decision_source():
    inspection = replace(_inspection(), affects_decision=True)
    with pytest.raises(PermissionError):
        _reporter().build(inspection)


def test_rc93_rejects_export_keep_below_one():
    inspection = replace(_inspection(), export_keep=0)
    with pytest.raises(ValueError):
        _reporter().build(inspection)


def test_rc93_rejects_inconsistent_counts():
    inspection = _inspection(existing=("a", "b"), retained=("a",), would_remove=())
    with pytest.raises(ValueError):
        _reporter().build(inspection)
