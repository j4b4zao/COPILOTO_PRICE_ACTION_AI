from types import SimpleNamespace

from app import voice_test_cli


class _Voice:
    def __init__(self, diagnostics, result=None):
        self._diagnostics = diagnostics
        self._result = result
        self.test_calls = 0

    def diagnostics(self):
        return self._diagnostics

    def test_audio(self, text=None):
        self.test_calls += 1
        return self._result


class _System:
    def __init__(self, voice):
        self.voice = voice


class _Initializer:
    system = None

    def __init__(self, *, voice_config=None):
        self.voice_config = voice_config

    def inicializar(self):
        return self.system


def _diag(*, ready=False):
    return SimpleNamespace(
        ready_for_real_audio=ready,
        to_dict=lambda: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": ready,
            "readonly": True,
            "affects_decision": False,
        },
    )


def _result(*, completed=True):
    return SimpleNamespace(
        completed=completed,
        to_dict=lambda: {
            "version": "RC47-CONTROLLED-REAL-AUDIO-TEST",
            "completed": completed,
            "readonly": True,
            "affects_decision": False,
        },
    )


def test_default_mode_runs_diagnostics_only(monkeypatch, capsys):
    voice = _Voice(_diag(ready=False))
    _Initializer.system = _System(voice)
    monkeypatch.setattr(voice_test_cli, "SystemInitializer", _Initializer)
    code = voice_test_cli.run([])
    assert code == 0
    assert voice.test_calls == 0
    assert "VOICE DIAGNOSTICS" in capsys.readouterr().out


def test_speak_is_blocked_when_diagnostics_not_ready(monkeypatch):
    voice = _Voice(_diag(ready=False))
    _Initializer.system = _System(voice)
    monkeypatch.setattr(voice_test_cli, "SystemInitializer", _Initializer)
    code = voice_test_cli.run(["--backend", "WINDOWS_SAPI", "--speak"])
    assert code == 2
    assert voice.test_calls == 0


def test_speak_executes_only_after_ready(monkeypatch):
    voice = _Voice(_diag(ready=True), _result(completed=True))
    _Initializer.system = _System(voice)
    monkeypatch.setattr(voice_test_cli, "SystemInitializer", _Initializer)
    code = voice_test_cli.run(["--backend", "WINDOWS_SAPI", "--speak"])
    assert code == 0
    assert voice.test_calls == 1


def test_failed_controlled_audio_returns_nonzero(monkeypatch):
    voice = _Voice(_diag(ready=True), _result(completed=False))
    _Initializer.system = _System(voice)
    monkeypatch.setattr(voice_test_cli, "SystemInitializer", _Initializer)
    code = voice_test_cli.run(["--backend", "WINDOWS_SAPI", "--speak"])
    assert code == 3


def test_cli_builds_requested_voice_config(monkeypatch):
    voice = _Voice(_diag(ready=False))
    _Initializer.system = _System(voice)
    monkeypatch.setattr(voice_test_cli, "SystemInitializer", _Initializer)
    voice_test_cli.run([
        "--backend", "windows_sapi",
        "--language", "en-GB",
        "--profile", "BRITISH_CALM_PRECISE_ASSISTANT",
        "--rate", "1.2",
    ])
    config = _Initializer(voice_config=None)
    assert voice.test_calls == 0


def test_parser_defaults_to_no_speak():
    args = voice_test_cli.build_parser().parse_args([])
    assert args.speak is False
    assert args.backend == "NULL_TTS"


def test_cli_module_does_not_touch_operational_decision():
    source = open(voice_test_cli.__file__, encoding="utf-8").read()
    for token in ("Strategy", "Score", "Risk", "Decision", "Alert"):
        assert f".{token.lower()}" not in source.lower()
