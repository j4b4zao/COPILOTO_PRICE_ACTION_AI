from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_export_rotation import (
    BookDiagnosticsVoiceStatusRetentionExportRotationManager,
)


class _WriteResult:
    def __init__(self, path):
        self.path = str(path)


class _FakeVoiceService:
    def __init__(self):
        self.calls = []

    def export_retention_status_file(self, directory, destination, *, keep=20, prefix="voice_status", generated_at=None):
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{"schema":"copiloto.voice.status.retention.v1"}', encoding="utf-8")
        self.calls.append((Path(directory), target, keep, prefix, generated_at))
        return _WriteResult(target)


def _manager():
    return BookDiagnosticsVoiceStatusRetentionExportRotationManager()


def test_rc87_creates_separate_retention_status_history(tmp_path):
    source = tmp_path / "voice"
    export = tmp_path / "retention-history"
    result = _manager().export_and_rotate(
        voice_service=_FakeVoiceService(),
        source_directory=source,
        export_directory=export,
    )
    assert result.version == "RC87-VOICE-STATUS-RETENTION-EXPORT-ROTATION"
    assert Path(result.current_file).exists()
    assert Path(result.current_file).name.startswith("voice_retention_status_")


def test_rc87_uses_rc85_service_contract(tmp_path):
    service = _FakeVoiceService()
    instant = datetime(2026, 8, 23, 16, 0, tzinfo=timezone.utc)
    _manager().export_and_rotate(
        voice_service=service,
        source_directory=tmp_path / "source",
        export_directory=tmp_path / "history",
        source_keep=7,
        source_prefix="voice_status",
        generated_at=instant,
    )
    assert len(service.calls) == 1
    assert service.calls[0][2:] == (7, "voice_status", instant)


def test_rc87_keeps_only_requested_export_count(tmp_path):
    service = _FakeVoiceService()
    folder = tmp_path / "history"
    manager = _manager()
    for second in range(3):
        manager.export_and_rotate(
            voice_service=service,
            source_directory=tmp_path / "source",
            export_directory=folder,
            export_keep=2,
            generated_at=datetime(2026, 8, 23, 16, 0, second, tzinfo=timezone.utc),
        )
    files = list(folder.glob("voice_retention_status_*.json"))
    assert len(files) == 2


def test_rc87_does_not_remove_normal_voice_snapshots(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    normal = source / "voice_status_001.json"
    normal.write_text("{}", encoding="utf-8")
    _manager().export_and_rotate(
        voice_service=_FakeVoiceService(),
        source_directory=source,
        export_directory=tmp_path / "history",
        export_keep=1,
    )
    assert normal.exists()


def test_rc87_preserves_unrelated_json_in_export_directory(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    unrelated = history / "other.json"
    unrelated.write_text("{}", encoding="utf-8")
    _manager().export_and_rotate(
        voice_service=_FakeVoiceService(),
        source_directory=tmp_path / "source",
        export_directory=history,
        export_keep=1,
    )
    assert unrelated.exists()


def test_rc87_custom_export_prefix_isolated(tmp_path):
    result = _manager().export_and_rotate(
        voice_service=_FakeVoiceService(),
        source_directory=tmp_path / "source",
        export_directory=tmp_path / "history",
        export_prefix="retention_audit",
    )
    assert result.export_prefix == "retention_audit"
    assert Path(result.current_file).name.startswith("retention_audit_")


def test_rc87_rejects_source_keep_below_one(tmp_path):
    with pytest.raises(ValueError):
        _manager().export_and_rotate(
            voice_service=_FakeVoiceService(),
            source_directory=tmp_path / "source",
            export_directory=tmp_path / "history",
            source_keep=0,
        )


def test_rc87_rejects_export_keep_below_one(tmp_path):
    with pytest.raises(ValueError):
        _manager().export_and_rotate(
            voice_service=_FakeVoiceService(),
            source_directory=tmp_path / "source",
            export_directory=tmp_path / "history",
            export_keep=0,
        )


def test_rc87_rejects_unsafe_prefix(tmp_path):
    with pytest.raises(ValueError):
        _manager().export_and_rotate(
            voice_service=_FakeVoiceService(),
            source_directory=tmp_path / "source",
            export_directory=tmp_path / "history",
            export_prefix="bad/prefix",
        )


def test_rc87_rejects_same_source_and_export_prefix(tmp_path):
    with pytest.raises(ValueError):
        _manager().export_and_rotate(
            voice_service=_FakeVoiceService(),
            source_directory=tmp_path / "source",
            export_directory=tmp_path / "history",
            source_prefix="same",
            export_prefix="same",
        )
