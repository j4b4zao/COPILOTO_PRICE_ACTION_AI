from types import SimpleNamespace

import pytest

import app.voice_status_retention_export_rotation_health_cli as cli


def _report(status="EMPTY", *, directory="/tmp/history", prefix="voice_retention_status", keep=20, existing=0, retained=0, remove=0):
    return SimpleNamespace(
        status=status,
        summary=f"summary-{status}",
        export_directory=directory,
        directory_exists=True,
        export_prefix=prefix,
        export_keep=keep,
        existing_count=existing,
        retained_count=retained,
        would_remove_count=remove,
        readonly=True,
    )


def _install_fake(monkeypatch, report, *, error=None):
    calls = {}

    class FakeVoice:
        def retention_status_exports_health(self, export_directory, *, export_keep=20, export_prefix="voice_retention_status"):
            calls["call"] = (export_directory, export_keep, export_prefix)
            if error is not None:
                raise error
            return report

    class FakeSystem:
        voice = FakeVoice()

    class FakeInitializer:
        def __init__(self, *, voice_config=None, **kwargs):
            calls["config"] = voice_config

        def inicializar(self):
            return FakeSystem()

    monkeypatch.setattr(cli, "SystemInitializer", FakeInitializer)
    return calls


def test_rc95_parser_has_no_audio_options():
    help_text = cli.build_parser().format_help()
    assert "--speak" not in help_text
    assert "--text" not in help_text
    assert "--enabled" not in help_text


def test_rc95_requires_export_directory():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_rc95_uses_safe_defaults(monkeypatch):
    calls = _install_fake(monkeypatch, _report())
    assert cli.run(["history"]) == 0
    assert calls["call"] == ("history", 20, "voice_retention_status")


def test_rc95_empty_returns_zero(monkeypatch, capsys):
    _install_fake(monkeypatch, _report("EMPTY"))
    assert cli.run(["history"]) == 0
    assert "STATUS: EMPTY" in capsys.readouterr().out


def test_rc95_within_limit_returns_zero(monkeypatch, capsys):
    _install_fake(monkeypatch, _report("WITHIN_LIMIT", existing=3, retained=3))
    assert cli.run(["history"]) == 0
    output = capsys.readouterr().out
    assert "STATUS: WITHIN_LIMIT" in output
    assert "EXISTING: 3" in output


def test_rc95_over_limit_returns_two(monkeypatch, capsys):
    _install_fake(monkeypatch, _report("OVER_LIMIT", keep=2, existing=4, retained=2, remove=2))
    assert cli.run(["history"]) == 2
    output = capsys.readouterr().out
    assert "STATUS: OVER_LIMIT" in output
    assert "WOULD_REMOVE: 2" in output


def test_rc95_passes_custom_keep_and_prefix(monkeypatch):
    calls = _install_fake(monkeypatch, _report(prefix="audit", keep=7))
    assert cli.run(["history", "--export-keep", "7", "--export-prefix", "audit"]) == 0
    assert calls["call"] == ("history", 7, "audit")


def test_rc95_keeps_voice_disabled_with_null_tts(monkeypatch):
    calls = _install_fake(monkeypatch, _report())
    cli.run(["history"])
    config = calls["config"]
    assert config.enabled is False
    assert config.backend == "NULL_TTS"


def test_rc95_propagates_invalid_keep_from_service(monkeypatch):
    _install_fake(monkeypatch, _report(), error=ValueError("export_keep must be >= 1"))
    with pytest.raises(ValueError):
        cli.run(["history", "--export-keep", "0"])


def test_rc95_prints_readonly_contract(monkeypatch, capsys):
    _install_fake(monkeypatch, _report("WITHIN_LIMIT", existing=1, retained=1))
    cli.run(["history"])
    output = capsys.readouterr().out
    assert "READONLY: True" in output
    assert "EXPORT_PREFIX: voice_retention_status" in output
