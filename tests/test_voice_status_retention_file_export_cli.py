from pathlib import Path

import json
import pytest

from app.voice_status_retention_file_export_cli import build_parser, run


def _snapshot(folder: Path, name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_rc86_parser_has_no_audio_options():
    help_text = build_parser().format_help()
    assert "--speak" not in help_text
    assert "--text" not in help_text
    assert "--enabled" not in help_text


def test_rc86_requires_source_and_destination():
    with pytest.raises(SystemExit):
        run([])


def test_rc86_empty_exports_json(tmp_path):
    source = tmp_path / "voice"
    destination = tmp_path / "out.json"
    code = run([str(source), str(destination)])
    assert code == 0
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["schema"] == "copiloto.voice.status.retention.v1"
    assert payload["status"] == "EMPTY"


def test_rc86_within_limit_returns_zero(tmp_path):
    source = tmp_path / "voice"
    _snapshot(source, "voice_status_001.json")
    destination = tmp_path / "out.json"
    code = run([str(source), str(destination), "--keep", "2"])
    assert code == 0
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["status"] == "WITHIN_LIMIT"


def test_rc86_over_limit_returns_two_without_deleting(tmp_path):
    source = tmp_path / "voice"
    files = [_snapshot(source, f"voice_status_{index}.json") for index in range(3)]
    destination = tmp_path / "out.json"
    code = run([str(source), str(destination), "--keep", "2"])
    assert code == 2
    assert all(path.exists() for path in files)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["status"] == "OVER_LIMIT"


def test_rc86_custom_prefix(tmp_path):
    source = tmp_path / "voice"
    _snapshot(source, "custom_001.json")
    _snapshot(source, "voice_status_001.json")
    destination = tmp_path / "out.json"
    code = run([str(source), str(destination), "--prefix", "custom"])
    assert code == 0
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["payload"]["inspection"]["prefix"] == "custom"
    assert len(payload["payload"]["inspection"]["existing_files"]) == 1


def test_rc86_invalid_keep_rejected(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), str(tmp_path / "out.json"), "--keep", "0"])


def test_rc86_invalid_prefix_rejected(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), str(tmp_path / "out.json"), "--prefix", "bad/prefix"])


def test_rc86_requires_json_destination(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), str(tmp_path / "out.txt")])


def test_rc86_creates_destination_parent_only_on_export(tmp_path):
    source = tmp_path / "voice"
    destination = tmp_path / "nested" / "status.json"
    assert destination.parent.exists() is False
    code = run([str(source), str(destination)])
    assert code == 0
    assert destination.exists() is True
