from pathlib import Path

import pytest

from app.voice_status_retention_export_rotation_inspection_cli import build_parser, run


def test_rc92_has_no_audio_options():
    parser = build_parser()
    options = {action.dest for action in parser._actions}
    assert "speak" not in options
    assert "text" not in options
    assert "enabled" not in options


def test_rc92_requires_export_directory():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_rc92_defaults_are_safe():
    args = build_parser().parse_args(["history"])
    assert args.export_keep == 20
    assert args.export_prefix == "voice_retention_status"


def test_rc92_missing_directory_is_not_created(tmp_path, capsys):
    target = tmp_path / "missing"
    assert run([str(target)]) == 0
    assert not target.exists()
    out = capsys.readouterr().out
    assert "DIRECTORY_EXISTS: False" in out


def test_rc92_lists_only_retention_export_series(tmp_path, capsys):
    history = tmp_path / "history"
    history.mkdir()
    (history / "voice_retention_status_001.json").write_text("{}", encoding="utf-8")
    (history / "voice_status_001.json").write_text("{}", encoding="utf-8")
    (history / "other.json").write_text("{}", encoding="utf-8")
    assert run([str(history)]) == 0
    out = capsys.readouterr().out
    assert "voice_retention_status_001.json" in out
    assert "voice_status_001.json" not in out
    assert "other.json" not in out


def test_rc92_reports_would_remove_without_deleting(tmp_path, capsys):
    history = tmp_path / "history"
    history.mkdir()
    files = []
    for index in range(3):
        path = history / f"voice_retention_status_{index:03d}.json"
        path.write_text("{}", encoding="utf-8")
        files.append(path)
    assert run([str(history), "--export-keep", "1"]) == 0
    out = capsys.readouterr().out
    assert "WOULD_REMOVE: 2" in out
    assert all(path.exists() for path in files)


def test_rc92_custom_prefix(tmp_path, capsys):
    history = tmp_path / "history"
    history.mkdir()
    custom = history / "retention_audit_001.json"
    custom.write_text("{}", encoding="utf-8")
    assert run([str(history), "--export-prefix", "retention_audit"]) == 0
    out = capsys.readouterr().out
    assert "PREFIX: retention_audit" in out
    assert custom.name in out


def test_rc92_rejects_export_keep_below_one(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), "--export-keep", "0"])


def test_rc92_rejects_unsafe_prefix(tmp_path):
    with pytest.raises(ValueError):
        run([str(tmp_path), "--export-prefix", "bad/prefix"])


def test_rc92_is_readonly_and_preserves_files(tmp_path, capsys):
    history = tmp_path / "history"
    history.mkdir()
    path = history / "voice_retention_status_001.json"
    path.write_text("{}", encoding="utf-8")
    before = path.read_bytes()
    assert run([str(history)]) == 0
    after = path.read_bytes()
    out = capsys.readouterr().out
    assert "READONLY: True" in out
    assert before == after
    assert path.exists()
