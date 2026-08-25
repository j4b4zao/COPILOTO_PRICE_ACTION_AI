from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _service():
    return BookDiagnosticsVoiceService(enabled=False)


def _stamp(second: int):
    return datetime(2026, 8, 23, 16, 30, second, tzinfo=timezone.utc)


def test_rc88_exposes_rc87_contract_with_default_series(tmp_path):
    source = tmp_path / "source"
    history = tmp_path / "history"
    result = _service().export_retention_status_rotated(source, history, generated_at=_stamp(1))
    assert result.version == "RC87-VOICE-STATUS-RETENTION-EXPORT-ROTATION"
    assert result.source_prefix == "voice_status"
    assert result.export_prefix == "voice_retention_status"
    assert Path(result.current_file).is_file()


def test_rc88_preserves_normal_voice_status_snapshots(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    normal = source / "voice_status_existing.json"
    normal.write_text("{}", encoding="utf-8")
    _service().export_retention_status_rotated(source, tmp_path / "history", generated_at=_stamp(2))
    assert normal.exists()


def test_rc88_applies_independent_export_keep(tmp_path):
    service = _service()
    source = tmp_path / "source"
    history = tmp_path / "history"
    for second in (3, 4, 5):
        service.export_retention_status_rotated(
            source,
            history,
            export_keep=2,
            generated_at=_stamp(second),
        )
    files = sorted(history.glob("voice_retention_status_*.json"))
    assert len(files) == 2


def test_rc88_preserves_unrelated_history_json(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    unrelated = history / "other.json"
    unrelated.write_text('{"keep": true}', encoding="utf-8")
    _service().export_retention_status_rotated(
        tmp_path / "source",
        history,
        export_keep=1,
        generated_at=_stamp(6),
    )
    assert json.loads(unrelated.read_text(encoding="utf-8")) == {"keep": True}


def test_rc88_supports_custom_source_and_export_prefixes(tmp_path):
    result = _service().export_retention_status_rotated(
        tmp_path / "source",
        tmp_path / "history",
        source_prefix="normal_voice",
        export_prefix="retention_history",
        generated_at=_stamp(7),
    )
    assert result.source_prefix == "normal_voice"
    assert result.export_prefix == "retention_history"
    assert Path(result.current_file).name.startswith("retention_history_")


def test_rc88_rejects_invalid_source_keep(tmp_path):
    with pytest.raises(ValueError):
        _service().export_retention_status_rotated(
            tmp_path / "source", tmp_path / "history", source_keep=0
        )


def test_rc88_rejects_invalid_export_keep(tmp_path):
    with pytest.raises(ValueError):
        _service().export_retention_status_rotated(
            tmp_path / "source", tmp_path / "history", export_keep=0
        )


def test_rc88_rejects_equal_source_and_export_prefixes(tmp_path):
    with pytest.raises(ValueError):
        _service().export_retention_status_rotated(
            tmp_path / "source",
            tmp_path / "history",
            source_prefix="same",
            export_prefix="same",
        )


def test_rc88_does_not_initialize_orchestrator(tmp_path):
    service = _service()
    assert service._orchestrator is None
    service.export_retention_status_rotated(
        tmp_path / "source", tmp_path / "history", generated_at=_stamp(8)
    )
    assert service._orchestrator is None


def test_rc88_result_is_readonly_and_decision_neutral(tmp_path):
    result = _service().export_retention_status_rotated(
        tmp_path / "source", tmp_path / "history", generated_at=_stamp(9)
    )
    assert result.readonly is True
    assert result.affects_decision is False
    payload = json.loads(Path(result.current_file).read_text(encoding="utf-8"))
    assert payload["schema"] == "copiloto.voice.status.retention.v1"
