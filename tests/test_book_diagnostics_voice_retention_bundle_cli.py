from pathlib import Path

import pytest

from app.voice_status_retention_bundle_cli import build_parser, run


def _snapshot(folder: Path, name: str) -> Path:
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_rc82_parser_has_no_audio_options():
    parser = build_parser()
    options = {opt for action in parser._actions for opt in action.option_strings}
    assert "--speak" not in options
    assert "--text" not in options


def test_rc82_directory_is_required():
    with pytest.raises(SystemExit):
        run([])


def test_rc82_empty_returns_zero(tmp_path, capsys):
    code = run([str(tmp_path)])
    output = capsys.readouterr().out
    assert code == 0
    assert "STATUS: EMPTY" in output


def test_rc82_within_limit_returns_zero(tmp_path, capsys):
    _snapshot(tmp_path, "voice_status_001.json")
    _snapshot(tmp_path, "voice_status_002.json")
    code = run([str(tmp_path), "--keep", "2"])
    output = capsys.readouterr().out
    assert code == 0
    assert "STATUS: WITHIN_LIMIT" in output
    assert "EXISTING_FILES: 2" in output


def test_rc82_over_limit_returns_two_without_deleting(tmp_path, capsys):
    files = [_snapshot(tmp_path, f"voice_status_{index}.json") for index in range(3)]
    code = run([str(tmp_path), "--keep", "2"])
    output = capsys.readouterr().out
    assert code == 2
    assert "STATUS: OVER_LIMIT" in output
    assert "WOULD_REMOVE_FILES: 1" in output
    assert all(path.exists() for path in files)


def test_rc82_json_output_contains_rc80_contract(tmp_path, capsys):
    code = run([str(tmp_path), "--json"])
    output = capsys.readouterr().out
    assert code == 0
    assert '"version": "RC80-VOICE-STATUS-RETENTION-BUNDLE"' in output
    assert '"readonly": true' in output.lower()


def test_rc82_custom_prefix(tmp_path, capsys):
    _snapshot(tmp_path, "custom_001.json")
    _snapshot(tmp_path, "voice_status_001.json")
    code = run([str(tmp_path), "--prefix", "custom"])
    output = capsys.readouterr().out
    assert code == 0
    assert "PREFIX: custom" in output
    assert "EXISTING_FILES: 1" in output


def test_rc82_missing_directory_is_not_created(tmp_path, capsys):
    missing = tmp_path / "missing"
    code = run([str(missing)])
    output = capsys.readouterr().out
    assert code == 0
    assert "DIRECTORY_EXISTS: False" in output
    assert missing.exists() is False


def test_rc82_invalid_keep_rejected(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), "--keep", "0"])


def test_rc82_invalid_prefix_rejected(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), "--prefix", "bad/prefix"])
