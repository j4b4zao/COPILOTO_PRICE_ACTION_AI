from pathlib import Path

import pytest

from app.voice_status_retention_health_cli import build_parser, run


def _snapshot(folder: Path, name: str) -> Path:
    path = folder / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_parser_has_no_audio_options():
    help_text = build_parser().format_help()
    assert "--speak" not in help_text
    assert "--text" not in help_text


def test_directory_is_required():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_defaults_are_safe(tmp_path):
    args = build_parser().parse_args([str(tmp_path)])
    assert args.keep == 20
    assert args.prefix == "voice_status"


def test_empty_directory_returns_zero(tmp_path, capsys):
    code = run([str(tmp_path)])
    output = capsys.readouterr().out
    assert code == 0
    assert "STATUS: EMPTY" in output
    assert "EXISTING: 0" in output
    assert "READONLY: True" in output


def test_missing_directory_is_not_created(tmp_path, capsys):
    missing = tmp_path / "missing"
    code = run([str(missing)])
    output = capsys.readouterr().out
    assert code == 0
    assert not missing.exists()
    assert "DIRECTORY_EXISTS: False" in output


def test_within_limit_returns_zero(tmp_path, capsys):
    _snapshot(tmp_path, "voice_status_1.json")
    _snapshot(tmp_path, "voice_status_2.json")
    code = run([str(tmp_path), "--keep", "2"])
    output = capsys.readouterr().out
    assert code == 0
    assert "STATUS: WITHIN_LIMIT" in output
    assert "EXISTING: 2" in output
    assert "EXCESS: 0" in output


def test_over_limit_returns_two_without_deleting(tmp_path, capsys):
    files = [
        _snapshot(tmp_path, "voice_status_1.json"),
        _snapshot(tmp_path, "voice_status_2.json"),
        _snapshot(tmp_path, "voice_status_3.json"),
    ]
    code = run([str(tmp_path), "--keep", "2"])
    output = capsys.readouterr().out
    assert code == 2
    assert "STATUS: OVER_LIMIT" in output
    assert "EXCESS: 1" in output
    assert all(path.exists() for path in files)


def test_custom_prefix_is_respected(tmp_path, capsys):
    _snapshot(tmp_path, "custom_1.json")
    _snapshot(tmp_path, "voice_status_1.json")
    code = run([str(tmp_path), "--prefix", "custom", "--keep", "1"])
    output = capsys.readouterr().out
    assert code == 0
    assert "PREFIX: custom" in output
    assert "EXISTING: 1" in output


def test_invalid_keep_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), "--keep", "0"])


def test_invalid_prefix_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), "--prefix", "bad prefix!"])
