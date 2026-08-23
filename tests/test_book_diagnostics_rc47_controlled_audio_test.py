from analysis.replay.book_diagnostics_tts_backend import TTSResult
from analysis.replay.book_diagnostics_tts_backend_registry import BookDiagnosticsTTSBackendRegistry
from analysis.replay.book_diagnostics_voice_audio_test import BookDiagnosticsControlledAudioTest
from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_diagnostics import VoiceCapabilitySnapshot
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


class _ReadyDiagnostics:
    def __init__(self, *, ready=True, backend="FAKE_TTS", error=None):
        self.ready = ready
        self.backend = backend
        self.error = error

    def inspect(self):
        return VoiceCapabilitySnapshot(
            version="RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            enabled=True,
            configured_backend=self.backend,
            backend_registered=True,
            backend_instantiable=True,
            backend_healthy=self.ready,
            language="pt-BR",
            voice_profile="BRITISH_CALM_PRECISE_ASSISTANT",
            speech_rate=1.0,
            available_voice_count=1 if self.ready else 0,
            selected_voice="Fake Voice" if self.ready else None,
            selection_reason="LANGUAGE_MATCH" if self.ready else None,
            ready_for_real_audio=self.ready,
            error=self.error,
        )


class _FakeBackend:
    name = "FAKE_TTS"

    def __init__(self):
        self.calls = 0

    def speak(self, command):
        self.calls += 1
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id=command.event_id,
            accepted=True,
            completed=True,
            interrupted=False,
            error="",
        )

    def stop(self, event_id=None):
        return False

    def healthcheck(self):
        return True


def _registry():
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("FAKE_TTS", _FakeBackend)
    return registry


def test_rc47_blocks_when_diagnostics_not_ready():
    test = BookDiagnosticsControlledAudioTest(
        config=VoiceConfig(enabled=True, backend="FAKE_TTS"),
        backend_registry=_registry(),
        diagnostics=_ReadyDiagnostics(ready=False),
    )
    result = test.run()
    assert result.executed is False
    assert result.accepted is False


def test_rc47_executes_only_after_ready():
    test = BookDiagnosticsControlledAudioTest(
        config=VoiceConfig(enabled=True, backend="FAKE_TTS"),
        backend_registry=_registry(),
        diagnostics=_ReadyDiagnostics(ready=True),
    )
    result = test.run(text="Teste controlado")
    assert result.executed is True
    assert result.accepted is True
    assert result.completed is True


def test_rc47_rejects_empty_text():
    test = BookDiagnosticsControlledAudioTest(
        config=VoiceConfig(enabled=True, backend="FAKE_TTS"),
        backend_registry=_registry(),
        diagnostics=_ReadyDiagnostics(ready=True),
    )
    try:
        test.run(text="   ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_rc47_rejects_long_text():
    test = BookDiagnosticsControlledAudioTest(
        config=VoiceConfig(enabled=True, backend="FAKE_TTS"),
        backend_registry=_registry(),
        diagnostics=_ReadyDiagnostics(ready=True),
    )
    try:
        test.run(text="x" * 161)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_rc47_result_is_readonly_and_non_operational():
    test = BookDiagnosticsControlledAudioTest(
        config=VoiceConfig(enabled=True, backend="FAKE_TTS"),
        backend_registry=_registry(),
        diagnostics=_ReadyDiagnostics(ready=True),
    )
    result = test.run()
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc47_service_exposes_explicit_test_method():
    service = BookDiagnosticsVoiceService(
        config=VoiceConfig(enabled=False, backend="NULL_TTS"),
    )
    result = service.test_audio()
    assert result.executed is False


def test_rc47_default_text_is_short():
    assert len(BookDiagnosticsControlledAudioTest.DEFAULT_TEXT) <= 160
