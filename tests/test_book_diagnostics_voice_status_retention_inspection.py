from __future__ import annotations

from pathlib import Path
import os

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_inspection import (
    BookDiagnosticsVoiceStatusRetentionInspector,
)


def _touch(path: Path, ns: int) -> None:
    path.write_text("{}", encoding="utf-8")
    os.utime(path, ns=(ns, ns))


def test_rc70_contract_is_readonly(tmp_path):
    result = BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path)
    assert result.version == "RC70-VOICE-STATUS-RETENTION-INSPECTION"
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc70_missing_directory_is_not_created(tmp_path):
    target = tmp_path / "missing"
    result = BookDiagnosticsVoiceStatusRetentionInspector().inspect(target)
    assert result.directory_exists is False
    assert result.existing_files == ()
    assert not target.exists()


def test_rc70_lists_only_matching_prefix_json(tmp_path):
    _touch(tmp_path / "voice_status_1.json", 1_000_000_000)
    _touch(tmp_path / "other.json", 2_000_000_000)
    _touch(tmp_path / "other_1.json", 3_000_000_000)
    result = BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path)
    assert len(result.existing_files) == 1
    assert result.existing_files[0].endswith("voice_status_1.json")


def test_rc70_orders_newest_first(tmp_path):
    _touch(tmp_path / "voice_status_old.json", 1_000_000_000)
    _touch(tmp_path / "voice_status_new.json", 2_000_000_000)
    result = BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path)
    assert result.existing_files[0].endswith("voice_status_new.json")


def test_rc70_reports_would_remove_without_deleting(tmp_path):
    for idx in range(3):
        _touch(tmp_path / f"voice_status_{idx}.json", (idx + 1) * 1_000_000_000)
    result = BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path, keep=2)
    assert len(result.retained_files) == 2
    assert len(result.would_remove_files) == 1
    assert len(list(tmp_path.glob("voice_status_*.json"))) == 3


def test_rc70_keep_must_be_positive(tmp_path):
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path, keep=0)


def test_rc70_reuses_safe_prefix_validation(tmp_path):
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path, prefix="../unsafe")


def test_rc70_supports_custom_prefix(tmp_path):
    _touch(tmp_path / "diag_1.json", 1_000_000_000)
    _touch(tmp_path / "voice_status_1.json", 2_000_000_000)
    result = BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path, prefix="diag")
    assert result.prefix == "diag"
    assert len(result.existing_files) == 1
    assert result.existing_files[0].endswith("diag_1.json")


def test_rc70_to_dict_preserves_contract(tmp_path):
    payload = BookDiagnosticsVoiceStatusRetentionInspector().inspect(tmp_path).to_dict()
    assert payload["version"] == "RC70-VOICE-STATUS-RETENTION-INSPECTION"
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_rc70_has_no_audio_or_mutation_methods():
    inspector = BookDiagnosticsVoiceStatusRetentionInspector()
    for name in ("speak", "test_audio", "dispatch", "export_and_rotate", "unlink", "write"):
        assert not hasattr(inspector, name)
