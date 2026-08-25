from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService
from analysis.replay.book_diagnostics_voice_status_retention import (
    BookDiagnosticsVoiceStatusRetentionManager,
)


def _service():
    return BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False, backend="NULL_TTS"))


def test_rc68_contract_and_readonly(tmp_path):
    result = _service().export_status_rotated(tmp_path, keep=3)
    assert result.version == "RC68-VOICE-STATUS-EXPORT-RETENTION"
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc68_creates_timestamped_json(tmp_path):
    instant = datetime(2026, 8, 23, 15, 0, 0, tzinfo=timezone.utc)
    result = _service().export_status_rotated(tmp_path, generated_at=instant)
    path = Path(result.current_file)
    assert path.name == "voice_status_20260823T150000000000Z.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "copiloto.voice.status.v1"


def test_rc68_keep_must_be_positive(tmp_path):
    with pytest.raises(ValueError):
        _service().export_status_rotated(tmp_path, keep=0)


def test_rc68_rejects_empty_prefix(tmp_path):
    with pytest.raises(ValueError):
        _service().export_status_rotated(tmp_path, prefix="")


def test_rc68_rejects_unsafe_prefix(tmp_path):
    with pytest.raises(ValueError):
        _service().export_status_rotated(tmp_path, prefix="../voice")


def test_rc68_retains_only_requested_count(tmp_path):
    service = _service()
    base = datetime(2026, 8, 23, 15, 0, 0, tzinfo=timezone.utc)
    for index in range(5):
        service.export_status_rotated(
            tmp_path,
            keep=3,
            generated_at=base + timedelta(seconds=index),
        )
    files = list(tmp_path.glob("voice_status_*.json"))
    assert len(files) == 3


def test_rc68_reports_removed_files(tmp_path):
    service = _service()
    base = datetime(2026, 8, 23, 15, 0, 0, tzinfo=timezone.utc)
    service.export_status_rotated(tmp_path, keep=2, generated_at=base)
    service.export_status_rotated(tmp_path, keep=2, generated_at=base + timedelta(seconds=1))
    result = service.export_status_rotated(tmp_path, keep=2, generated_at=base + timedelta(seconds=2))
    assert len(result.removed_files) == 1
    assert len(result.retained_files) == 2


def test_rc68_does_not_delete_unrelated_json(tmp_path):
    unrelated = tmp_path / "market_snapshot.json"
    unrelated.write_text("{}", encoding="utf-8")
    service = _service()
    base = datetime(2026, 8, 23, 15, 0, 0, tzinfo=timezone.utc)
    for index in range(3):
        service.export_status_rotated(tmp_path, keep=1, generated_at=base + timedelta(seconds=index))
    assert unrelated.exists()


def test_rc68_custom_prefix_is_isolated(tmp_path):
    service = _service()
    base = datetime(2026, 8, 23, 15, 0, 0, tzinfo=timezone.utc)
    service.export_status_rotated(tmp_path, keep=1, prefix="voice_a", generated_at=base)
    service.export_status_rotated(tmp_path, keep=1, prefix="voice_b", generated_at=base + timedelta(seconds=1))
    service.export_status_rotated(tmp_path, keep=1, prefix="voice_a", generated_at=base + timedelta(seconds=2))
    assert len(list(tmp_path.glob("voice_a_*.json"))) == 1
    assert len(list(tmp_path.glob("voice_b_*.json"))) == 1


def test_rc68_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.export_status_rotated(tmp_path, keep=2)
    assert service._orchestrator is None
