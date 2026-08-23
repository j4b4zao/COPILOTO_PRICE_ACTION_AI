from pathlib import Path

import pytest

from app import voice_status_retention_inspection_cli as cli


def test_parser_has_no_audio_options():
    parser = cli.build_parser()
    option_strings = {item for action in parser._actions for item in action.option_strings}
    assert "--speak" not in option_strings
    assert "--text" not in option_strings


def test_directory_is_required():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_defaults_are_safe():
    args = cli.build_parser().parse_args(["logs/voice"])
    assert args.keep == 20
    assert args.prefix == "voice_status"


def test_missing_directory_is_not_created(tmp_path):
    target = tmp_path / "missing"
    assert not target.exists()
    assert cli.run([str(target)]) == 0
    assert not target.exists()


def test_existing_files_are_not_removed(tmp_path):
    folder = tmp_path / "voice"
    folder.mkdir()
    files = []
    for index in range(3):
        path = folder / f"voice_status_20260101T00000{index}000000Z.json"
        path.write_text("{}", encoding="utf-8")
        files.append(path)
    assert cli.run([str(folder), "--keep", "1"]) == 0
    assert all(path.exists() for path in files)


def test_custom_prefix_filters_scope(tmp_path):
    folder = tmp_path / "voice"
    folder.mkdir()
    (folder / "custom_20260101T000000000000Z.json").write_text("{}", encoding="utf-8")
    (folder / "voice_status_20260101T000000000000Z.json").write_text("{}", encoding="utf-8")
    assert cli.run([str(folder), "--prefix", "custom"]) == 0


def test_keep_must_be_positive(tmp_path):
    with pytest.raises(ValueError):
        cli.run([str(tmp_path), "--keep", "0"])


def test_invalid_prefix_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        cli.run([str(tmp_path), "--prefix", "../bad"])


def test_run_does_not_create_json(tmp_path):
    folder = tmp_path / "voice"
    folder.mkdir()
    before = set(folder.glob("*.json"))
    assert cli.run([str(folder)]) == 0
    after = set(folder.glob("*.json"))
    assert after == before


def test_cli_source_has_no_audio_calls():
    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert ".speak(" not in source
    assert "test_audio(" not in source
    assert "dispatch_projection(" not in source
