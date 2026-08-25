from __future__ import annotations

from pathlib import Path

import pytest

from app.voice_status_retention_export_rotation_cli import build_parser, run


def _touch(path: Path, text: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_parser_has_no_audio_options():
    help_text = build_parser().format_help()
    assert "--speak" not in help_text
    assert "--text" not in help_text
    assert "--enabled" not in help_text


def test_source_and_export_directories_are_required():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_empty_source_creates_separate_export_history(tmp_path: Path):
    source = tmp_path / "source"
    export = tmp_path / "history"
    code = run([str(source), str(export)])
    assert code == 0
    files = list(export.glob("voice_retention_status_*.json"))
    assert len(files) == 1


def test_defaults_keep_normal_and_history_prefixes_separate(tmp_path: Path):
    source = tmp_path / "source"
    export = tmp_path / "history"
    source.mkdir()
    _touch(source / "voice_status_20260101T000000000000Z.json")
    run([str(source), str(export)])
    assert (source / "voice_status_20260101T000000000000Z.json").exists()
    assert len(list(export.glob("voice_retention_status_*.json"))) == 1


def test_export_keep_limits_only_history_series(tmp_path: Path):
    source = tmp_path / "source"
    export = tmp_path / "history"
    source.mkdir()
    export.mkdir()
    _touch(export / "voice_retention_status_20260101T000000000000Z.json")
    _touch(export / "voice_retention_status_20260102T000000000000Z.json")
    run([str(source), str(export), "--export-keep", "1"])
    assert len(list(export.glob("voice_retention_status_*.json"))) == 1


def test_unrelated_json_is_preserved(tmp_path: Path):
    source = tmp_path / "source"
    export = tmp_path / "history"
    unrelated = export / "other.json"
    _touch(unrelated)
    run([str(source), str(export), "--export-keep", "1"])
    assert unrelated.exists()


def test_custom_prefixes_are_supported(tmp_path: Path):
    source = tmp_path / "source"
    export = tmp_path / "history"
    source.mkdir()
    _touch(source / "normal_20260101T000000000000Z.json")
    run([
        str(source),
        str(export),
        "--source-prefix", "normal",
        "--export-prefix", "retention_history",
    ])
    assert len(list(export.glob("retention_history_*.json"))) == 1
    assert (source / "normal_20260101T000000000000Z.json").exists()


def test_invalid_source_keep_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        run([str(tmp_path / "source"), str(tmp_path / "history"), "--source-keep", "0"])


def test_invalid_export_keep_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        run([str(tmp_path / "source"), str(tmp_path / "history"), "--export-keep", "0"])


def test_equal_prefixes_are_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        run([
            str(tmp_path / "source"),
            str(tmp_path / "history"),
            "--source-prefix", "same",
            "--export-prefix", "same",
        ])
