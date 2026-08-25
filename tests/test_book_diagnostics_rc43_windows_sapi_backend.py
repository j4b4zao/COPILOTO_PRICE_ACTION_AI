import base64

from analysis.replay.book_diagnostics_tts_backend_registry import (
    BookDiagnosticsTTSBackendRegistry,
)
from analysis.replay.book_diagnostics_windows_sapi_backend import WindowsSAPITTSBackend


def _command(**changes):
    payload = {
        "version": "RC33-VOICE-OUTPUT-ADAPTER",
        "command": "SPEAK",
        "event_id": "voice-rc43",
        "text": "Mercado em observacao.",
        "priority": "NORMAL",
        "interrupt": False,
        "voice_profile": "BRITISH_CALM_PRECISE_ASSISTANT",
        "language": "pt-BR",
        "speech_rate": 1.0,
        "estimated_duration_seconds": 2.0,
        "source_version": "RC31-VOICE-EVENT-CONTRACT",
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


class FakeProcess:
    def __init__(self, *, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr
        self.terminated = False

    def communicate(self):
        return "", self.stderr

    def terminate(self):
        self.terminated = True


class CapturingPopen:
    def __init__(self, process=None):
        self.process = process or FakeProcess()
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        return self.process


def _which(name):
    if name == "powershell":
        return r"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
    return None


def test_registry_exposes_windows_sapi_but_keeps_null_default():
    registry = BookDiagnosticsTTSBackendRegistry()
    assert registry.contains("WINDOWS_SAPI") is True
    assert registry.snapshot().default_backend == "NULL_TTS"


def test_registry_creates_windows_sapi_backend_explicitly():
    backend = BookDiagnosticsTTSBackendRegistry().create("windows_sapi")
    assert isinstance(backend, WindowsSAPITTSBackend)
    assert backend.name == "WINDOWS_SAPI"


def test_healthcheck_rejects_non_windows_host():
    backend = WindowsSAPITTSBackend(platform_name="Linux", which=_which)
    assert backend.healthcheck() is False


def test_healthcheck_requires_powershell():
    backend = WindowsSAPITTSBackend(platform_name="Windows", which=lambda _: None)
    assert backend.healthcheck() is False


def test_healthcheck_accepts_windows_with_powershell():
    backend = WindowsSAPITTSBackend(platform_name="Windows", which=_which)
    assert backend.healthcheck() is True


def test_speak_returns_controlled_error_when_backend_unavailable():
    backend = WindowsSAPITTSBackend(platform_name="Linux", which=lambda _: None)
    result = backend.speak(_command())
    assert result.backend == "WINDOWS_SAPI"
    assert result.accepted is False
    assert result.completed is False
    assert "unavailable" in result.error
    assert result.readonly is True
    assert result.affects_decision is False


def test_speak_executes_powershell_and_completes():
    popen = CapturingPopen(FakeProcess(returncode=0))
    backend = WindowsSAPITTSBackend(
        platform_name="Windows",
        which=_which,
        popen_factory=popen,
    )
    result = backend.speak(_command(text="Teste seguro de voz."))
    assert result.accepted is True
    assert result.completed is True
    assert result.error == ""
    assert len(popen.calls) == 1
    args, _ = popen.calls[0]
    assert "-NoProfile" in args
    assert "System.Speech" in args[-1]


def test_text_is_base64_encoded_in_script_not_interpolated_raw():
    text = "Texto com ' aspas; $variavel e caracteres especiais"
    popen = CapturingPopen()
    backend = WindowsSAPITTSBackend(platform_name="Windows", which=_which, popen_factory=popen)
    backend.speak(_command(text=text))
    script = popen.calls[0][0][-1]
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    assert encoded in script
    assert text not in script


def test_sapi_rate_mapping_is_bounded():
    assert WindowsSAPITTSBackend._sapi_rate(0.5) >= -10
    assert WindowsSAPITTSBackend._sapi_rate(1.0) == 0
    assert WindowsSAPITTSBackend._sapi_rate(2.0) <= 10


def test_nonzero_process_exit_becomes_tts_error():
    popen = CapturingPopen(FakeProcess(returncode=1, stderr="speech failed"))
    backend = WindowsSAPITTSBackend(platform_name="Windows", which=_which, popen_factory=popen)
    result = backend.speak(_command())
    assert result.accepted is True
    assert result.completed is False
    assert result.error == "speech failed"


def test_popen_failure_becomes_controlled_tts_error():
    def broken_popen(*args, **kwargs):
        raise OSError("cannot start")

    backend = WindowsSAPITTSBackend(platform_name="Windows", which=_which, popen_factory=broken_popen)
    result = backend.speak(_command())
    assert result.accepted is False
    assert "cannot start" in result.error


def test_stop_without_active_process_is_safe_noop():
    backend = WindowsSAPITTSBackend(platform_name="Windows", which=_which)
    assert backend.stop() is False


def test_wrong_rc33_command_is_rejected_before_io():
    popen = CapturingPopen()
    backend = WindowsSAPITTSBackend(platform_name="Windows", which=_which, popen_factory=popen)
    try:
        backend.speak(_command(version="RC32"))
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")
    assert popen.calls == []
