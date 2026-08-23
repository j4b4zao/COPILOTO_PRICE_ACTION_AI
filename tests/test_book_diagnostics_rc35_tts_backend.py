from analysis.replay.book_diagnostics_tts_backend import (
    BookDiagnosticsTTSGateway,
    NullTTSBackend,
    TTSResult,
)


def _command(**changes):
    payload = {
        "version": "RC33-VOICE-OUTPUT-ADAPTER",
        "command": "SPEAK",
        "event_id": "voice-rc35-test",
        "text": "Contexto de mercado pronto para observacao.",
        "priority": "NORMAL",
        "interrupt": False,
        "voice_profile": "BRITISH_CALM_PRECISE_ASSISTANT",
        "language": "pt-BR",
        "speech_rate": 1.0,
        "estimated_duration_seconds": 2.5,
        "source_version": "RC31-VOICE-EVENT-CONTRACT",
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def test_null_backend_is_healthy_and_named():
    gateway = BookDiagnosticsTTSGateway()
    assert gateway.healthcheck() is True
    assert gateway.backend_name() == "NULL_TTS"


def test_null_backend_accepts_rc33_command():
    result = BookDiagnosticsTTSGateway().speak(_command())
    assert isinstance(result, TTSResult)
    assert result.accepted is True
    assert result.completed is True
    assert result.interrupted is False
    assert result.readonly is True
    assert result.affects_decision is False


def test_result_keeps_event_id():
    result = BookDiagnosticsTTSGateway().speak(_command(event_id="voice-abc"))
    assert result.event_id == "voice-abc"


def test_null_backend_stop_is_safe_noop():
    gateway = BookDiagnosticsTTSGateway(backend=NullTTSBackend())
    assert gateway.stop() is False
    assert gateway.stop("voice-abc") is False


def test_empty_stop_event_id_is_rejected():
    gateway = BookDiagnosticsTTSGateway()
    try:
        gateway.stop("   ")
    except ValueError as exc:
        assert "event_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_wrong_command_version_is_rejected():
    try:
        BookDiagnosticsTTSGateway().speak(_command(version="RC32"))
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_non_speak_command_is_rejected():
    try:
        BookDiagnosticsTTSGateway().speak(_command(command="STOP"))
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_non_readonly_command_is_rejected():
    try:
        BookDiagnosticsTTSGateway().speak(_command(readonly=False))
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_decision_affecting_command_is_rejected():
    try:
        BookDiagnosticsTTSGateway().speak(_command(affects_decision=True))
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_invalid_priority_is_rejected():
    try:
        BookDiagnosticsTTSGateway().speak(_command(priority="CRITICAL"))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_non_positive_speech_rate_is_rejected():
    try:
        BookDiagnosticsTTSGateway().speak(_command(speech_rate=0))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_non_positive_duration_is_rejected():
    try:
        BookDiagnosticsTTSGateway().speak(_command(estimated_duration_seconds=0))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


class FakeBackend:
    name = "FAKE"

    def speak(self, command):
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id=command["event_id"],
            accepted=True,
            completed=False,
            interrupted=False,
            error="",
        )

    def stop(self, event_id=None):
        return True

    def healthcheck(self):
        return True


def test_custom_backend_can_be_injected():
    gateway = BookDiagnosticsTTSGateway(backend=FakeBackend())
    result = gateway.speak(_command())
    assert gateway.backend_name() == "FAKE"
    assert result.accepted is True
    assert result.completed is False
    assert gateway.stop("voice-rc35-test") is True


class BadEventBackend(FakeBackend):
    def speak(self, command):
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id="wrong-id",
            accepted=True,
            completed=True,
            interrupted=False,
            error="",
        )


def test_backend_result_event_mismatch_is_rejected():
    try:
        BookDiagnosticsTTSGateway(backend=BadEventBackend()).speak(_command())
    except ValueError as exc:
        assert "event_id mismatch" in str(exc)
    else:
        raise AssertionError("expected ValueError")


class DecisionAffectingResultBackend(FakeBackend):
    def speak(self, command):
        return {
            "version": "RC35-TTS-BACKEND-CONTRACT",
            "backend": self.name,
            "event_id": command["event_id"],
            "accepted": True,
            "completed": True,
            "interrupted": False,
            "error": "",
            "readonly": True,
            "affects_decision": True,
        }


def test_decision_affecting_backend_result_is_rejected():
    try:
        BookDiagnosticsTTSGateway(backend=DecisionAffectingResultBackend()).speak(_command())
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")
