import pytest

from analysis.replay.book_diagnostics_runtime_event_bridge import (
    BookDiagnosticsRuntimeEventBridge,
)
from analysis.replay.book_diagnostics_tts_backend import BookDiagnosticsTTSGateway, TTSResult
from analysis.replay.book_diagnostics_tts_runtime import BookDiagnosticsTTSRuntimeCoordinator
from analysis.replay.book_diagnostics_voice_runtime_facade import (
    BookDiagnosticsVoiceRuntimeFacade,
    VoiceRuntimeFacadeSnapshot,
)


def _message(**changes):
    payload = {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "should_emit": True,
        "priority": "NORMAL",
        "reason": "MESSAGE_APPROVED",
        "message": "Leitura do mercado pronta para observacao.",
        "fingerprint": "abc123",
        "cooldown_seconds": 180,
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def test_initial_snapshot_is_safe_and_readonly():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    snap = facade.snapshot()
    assert isinstance(snap, VoiceRuntimeFacadeSnapshot)
    assert snap.version == "RC38-VOICE-RUNTIME-FACADE"
    assert snap.queue_size == 0
    assert snap.session_state == "IDLE"
    assert snap.readonly is True
    assert snap.affects_decision is False


def test_submit_message_delegates_to_rc37():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    decision = facade.submit_message(_message())
    assert decision.accepted is True
    assert decision.emitted is True
    assert facade.snapshot().queue_size == 1


def test_suppressed_message_does_not_enter_queue():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    decision = facade.submit_message(
        _message(should_emit=False, reason="DUPLICATE_WITHIN_COOLDOWN")
    )
    assert decision.accepted is False
    assert decision.emitted is False
    assert facade.snapshot().queue_size == 0


def test_submit_and_process_runs_full_chain_with_null_backend():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    decision, result = facade.submit_and_process(_message())
    assert decision.accepted is True
    assert result.accepted is True
    assert result.completed is True
    snap = facade.snapshot()
    assert snap.session_state == "IDLE"
    assert snap.last_status == "COMPLETED"
    assert snap.last_event_id == decision.event_id


def test_process_next_handles_already_queued_message():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    facade.submit_message(_message())
    result = facade.process_next()
    assert result.completed is True
    assert facade.snapshot().queue_size == 0


def test_reset_clears_runtime_state():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    facade.submit_message(_message())
    snap = facade.reset()
    assert snap.queue_size == 0
    assert snap.session_state == "IDLE"
    assert snap.last_event_id is None
    assert snap.last_status is None


def test_stop_active_returns_false_when_idle():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    assert facade.stop_active() is False


class AsyncBackend:
    name = "ASYNC"

    def speak(self, command):
        event_id = command.event_id if hasattr(command, "event_id") else command["event_id"]
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id=event_id,
            accepted=True,
            completed=False,
            interrupted=False,
            error="",
        )

    def stop(self, event_id=None):
        return True

    def healthcheck(self):
        return True


def _async_facade():
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=AsyncBackend())
    )
    return BookDiagnosticsVoiceRuntimeFacade(
        bridge=BookDiagnosticsRuntimeEventBridge(runtime=runtime)
    )


def test_async_backend_exposes_speaking_state():
    facade = _async_facade()
    _, result = facade.submit_and_process(_message())
    assert result.completed is False
    snap = facade.snapshot()
    assert snap.session_state == "SPEAKING"
    assert snap.last_status == "SPEAKING"


def test_complete_active_is_available_through_facade():
    facade = _async_facade()
    decision, _ = facade.submit_and_process(_message())
    snap = facade.complete_active(event_id=decision.event_id)
    assert snap.state == "IDLE"
    assert facade.snapshot().last_status == "COMPLETED"


def test_fail_active_is_available_through_facade():
    facade = _async_facade()
    decision, _ = facade.submit_and_process(_message())
    snap = facade.fail_active("backend timeout", event_id=decision.event_id)
    assert snap.state == "FAILED"
    assert facade.snapshot().last_error == "backend timeout"


def test_urgent_message_can_interrupt_through_facade():
    facade = _async_facade()
    facade.submit_and_process(_message(message="normal", priority="NORMAL"))
    decision, result = facade.submit_and_process(
        _message(message="urgent", priority="URGENT", fingerprint="urgent-fp")
    )
    assert decision.accepted is True
    assert result.accepted is True
    assert facade.snapshot().active_event_id == decision.event_id


def test_nonurgent_message_waits_when_backend_is_busy():
    facade = _async_facade()
    facade.submit_and_process(_message(message="first"))
    decision, result = facade.submit_and_process(
        _message(message="second", fingerprint="second-fp")
    )
    assert decision.accepted is True
    assert result is None
    snap = facade.snapshot()
    assert snap.last_status == "BUSY"
    assert snap.queue_size == 1


def test_rc30_validation_is_preserved_by_facade():
    facade = BookDiagnosticsVoiceRuntimeFacade()
    with pytest.raises(PermissionError):
        facade.submit_message(_message(affects_decision=True))


def test_snapshot_validation_rejects_decision_affecting_runtime():
    class BadBridge:
        runtime = None

        def snapshot(self):
            return {
                "version": "RC36-TTS-RUNTIME-COORDINATOR",
                "queue_size": 0,
                "session_state": "IDLE",
                "active_event_id": None,
                "backend": "BAD",
                "backend_healthy": True,
                "last_event_id": None,
                "last_status": None,
                "last_error": None,
                "readonly": True,
                "affects_decision": True,
            }

    facade = BookDiagnosticsVoiceRuntimeFacade(bridge=BadBridge())
    with pytest.raises(PermissionError):
        facade.snapshot()
