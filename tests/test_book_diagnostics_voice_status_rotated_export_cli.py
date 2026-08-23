from __future__ import annotations

from pathlib import Path

import pytest

from app import voice_status_rotated_export_cli as cli


def test_parser_has_no_audio_options():
    parser = cli.build_parser()
    options = {opt for action in parser._actions for opt in action.option_strings}
    assert "--speak" not in options
    assert "--text" not in options


def test_parser_defaults_are_safe(tmp_path):
    args = cli.build_parser().parse_args([str(tmp_path)])
    assert args.keep == 20
    assert args.prefix == "voice_status"
    assert args.backend == "NULL_TTS"
    assert args.enabled is False


def test_directory_is_required():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_keep_override(tmp_path):
    args = cli.build_parser().parse_args([str(tmp_path), "--keep", "3"])
    assert args.keep == 3


def test_prefix_override(tmp_path):
    args = cli.build_parser().parse_args([str(tmp_path), "--prefix", "diag_voice"])
    assert args.prefix == "diag_voice"


def test_run_creates_rotated_snapshot(tmp_path):
    code = cli.run([str(tmp_path)])
    assert code == 0
    files = list(Path(tmp_path).glob("voice_status_*.json"))
    assert len(files) == 1


def test_run_respects_custom_prefix(tmp_path):
    code = cli.run([str(tmp_path), "--prefix", "diag_voice"])
    assert code == 0
    files = list(Path(tmp_path).glob("diag_voice_*.json"))
    assert len(files) == 1


def test_run_respects_retention(tmp_path):
    for index in range(4):
        path = Path(tmp_path) / f"voice_status_20000101T00000{index}Z.json"
        path.write_text("{}", encoding="utf-8")
    code = cli.run([str(tmp_path), "--keep", "2"])
    assert code == 0
    files = list(Path(tmp_path).glob("voice_status_*.json"))
    assert len(files) == 2


def test_run_preserves_unrelated_json(tmp_path):
    other = Path(tmp_path) / "other.json"
    other.write_text("{}", encoding="utf-8")
    cli.run([str(tmp_path), "--keep", "1"])
    assert other.exists()


def test_entrypoint_exists():
    assert callable(cli.main)
