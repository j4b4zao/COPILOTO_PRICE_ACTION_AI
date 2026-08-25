from pathlib import Path

import pytest

from app.voice_status_export_cli import build_parser, run


def test_rc67_parser_has_no_audio_options():
    parser = build_parser()
    option_strings = {opt for action in parser._actions for opt in action.option_strings}
    assert "--speak" not in option_strings
    assert "--text" not in option_strings


def test_rc67_requires_destination():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_rc67_defaults_are_safe():
    args = build_parser().parse_args(["status.json"])
    assert args.enabled is False
    assert args.backend == "NULL_TTS"
    assert args.language == "pt-BR"


def test_rc67_export_creates_json(tmp_path, capsys):
    target = tmp_path / "voice_status.json"
    code = run([str(target)])
    assert code == 0
    assert target.exists()
    assert target.suffix == ".json"
    output = capsys.readouterr().out
    assert "VOICE STATUS EXPORT" in output
    assert "SCHEMA: copiloto.voice.status.v1" in output


def test_rc67_creates_parent_directories(tmp_path):
    target = tmp_path / "nested" / "voice" / "status.json"
    code = run([str(target)])
    assert code == 0
    assert target.exists()


def test_rc67_rejects_non_json_destination(tmp_path):
    target = tmp_path / "status.txt"
    with pytest.raises(ValueError):
        run([str(target)])


def test_rc67_prints_readonly(tmp_path, capsys):
    target = tmp_path / "status.json"
    run([str(target)])
    assert "READONLY: True" in capsys.readouterr().out


def test_rc67_supports_backend_overrides(tmp_path):
    target = tmp_path / "status.json"
    code = run([str(target), "--backend", "NULL_TTS", "--language", "pt-BR", "--profile", "BRITISH_CALM_PRECISE_ASSISTANT", "--rate", "1.0"])
    assert code == 0


def test_rc67_export_payload_has_schema(tmp_path):
    import json
    target = tmp_path / "status.json"
    run([str(target)])
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schema"] == "copiloto.voice.status.v1"
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_rc67_does_not_expose_audio_methods_in_cli_source():
    source = Path(__file__).resolve().parents[1] / "app" / "voice_status_export_cli.py"
    text = source.read_text(encoding="utf-8")
    assert "test_audio(" not in text
    assert ".speak(" not in text
