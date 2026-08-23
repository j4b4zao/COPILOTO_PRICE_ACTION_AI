import pytest

from analysis.replay.book_diagnostics_tts_backend import (
    BookDiagnosticsTTSGateway,
    TTSResult,
)
from analysis.replay.book_diagnostics_tts_runtime import (
    BookDiagnosticsTTSRuntimeCoordinator,
)


def _event(event_id="voice-1", priority="NORMAL", **changes):
    payload = {
        "version": "RC31-VOICE-EVENT-CONTRACT",
        "event_id": event_id,
        "text": f"Mensagem {event_id}",
        "priority": priority,
        "interrupt_allowed": priority == "URGENT",
        "estimated_duration_seconds": 2.0,
        "voice_profile": "BRITISH_CALM_PRECISE_ASSISTANT",
        "language": "pt-BR",
        "speech_rate": 1.0,
        "source_version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def test_initial_snapshot_is_idle_and_safe():
    runtime = BookDiagnosticsTTSRuntimeCoordinator()
    snap = runtime.snapshot()
    assert snap.version == "RC36-TTS-RUNTIME-COORDINATOR"
    assert snap.queue_size == 0
    assert snap.session_state == "IDLE"
    assert snap.backend == "NULL_TTS"
    assert snap.backend_healthy is True
    assert snap.readonly is True
    assert snap.affects_decision is False


def test_enqueue_delegates_to_rc32():
    runtime = BookDiagnosticsTTSRuntimeCoordinator()
    decision = runtime.enqueue(_event())
    assert decision.accepted is True
    assert runtime.snapshot().queue_size == 1


def test_process_next_with_null_backend_completes():
    runtime = BookDiagnosticsTTSRuntimeCoordinator()
    runtime.enqueue(_event("voice-a"))
    result = runtime.process_next()
    assert result.accepted is True
    assert result.completed is True
    snap = runtime.snapshot()
    assert snap.queue_size == 0
    assert snap.session_state == "IDLE"
    assert snap.last_event_id == "voice-a"
    assert snap.last_status == "COMPLETED"


def test_empty_runtime_returns_none():
    runtime = BookDiagnosticsTTSRuntimeCoordinator()
    assert runtime.process_next() is None
    assert runtime.snapshot().last_status == "EMPTY"


class AsyncBackend:
    name = "ASYNC"

    def __init__(self):
        self.stopped = []

    def speak(self, command):
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id=command.event_id,
            accepted=True,
            completed=False,
            interrupted=False,
            error="",
        )

    def stop(self, event_id=None):
        self.stopped.append(event_id)
        return True

    def healthcheck(self):
        return True


def test_async_backend_leaves_session_speaking():
    backend = AsyncBackend()
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=backend)
    )
    runtime.enqueue(_event("voice-a"))
    runtime.process_next()
    snap = runtime.snapshot()
    assert snap.session_state == "SPEAKING"
    assert snap.active_event_id == "voice-a"
    assert snap.last_status == "SPEAKING"


def test_busy_runtime_does_not_pop_normal_event():
    backend = AsyncBackend()
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=backend)
    )
    runtime.enqueue(_event("voice-a"))
    runtime.process_next()
    runtime.enqueue(_event("voice-b", "NORMAL"))
    assert runtime.process_next() is None
    assert runtime.snapshot().last_status == "BUSY"
    assert runtime.snapshot().queue_size == 1


def test_urgent_event_interrupts_active_session():
    backend = AsyncBackend()
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=backend)
    )
    runtime.enqueue(_event("voice-a"))
    runtime.process_next()
    runtime.enqueue(_event("voice-b", "URGENT"))
    result = runtime.process_next()
    assert result.event_id == "voice-b"
    assert backend.stopped == ["voice-a"]
    snap = runtime.snapshot()
    assert snap.active_event_id == "voice-b"
    assert snap.last_status == "SPEAKING"


def test_manual_completion_closes_async_session():
    backend = AsyncBackend()
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=backend)
    )
    runtime.enqueue(_event("voice-a"))
    runtime.process_next()
    snap = runtime.complete_active(event_id="voice-a")
    assert snap.state == "IDLE"
    assert runtime.snapshot().last_status == "COMPLETED"


def test_stop_active_calls_backend_and_returns_idle():
    backend = AsyncBackend()
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=backend)
    )
    runtime.enqueue(_event("voice-a"))
    runtime.process_next()
    assert runtime.stop_active() is True
    assert backend.stopped == ["voice-a"]
    assert runtime.snapshot().session_state == "IDLE"
    assert runtime.snapshot().last_status == "STOPPED"


def test_stop_active_is_false_when_idle():
    runtime = BookDiagnosticsTTSRuntimeCoordinator()
    assert runtime.stop_active() is False


class ErrorResultBackend(AsyncBackend):
    name = "ERROR_RESULT"

    def speak(self, command):
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id=command.event_id,
            accepted=True,
            completed=False,
            interrupted=False,
            error="backend unavailable",
        )


def test_backend_error_result_moves_session_to_failed():
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=ErrorResultBackend())
    )
    runtime.enqueue(_event())
    result = runtime.process_next()
    assert result.error == "backend unavailable"
    snap = runtime.snapshot()
    assert snap.session_state == "FAILED"
    assert snap.last_status == "FAILED"
    assert snap.last_error == "backend unavailable"


class RaisingBackend(AsyncBackend):
    name = "RAISING"

    def speak(self, command):
        raise RuntimeError("tts crash")


def test_backend_exception_marks_failed_and_reraises():
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=RaisingBackend())
    )
    runtime.enqueue(_event())
    with pytest.raises(RuntimeError, match="tts crash"):
        runtime.process_next()
    snap = runtime.snapshot()
    assert snap.session_state == "FAILED"
    assert snap.last_status == "FAILED"
    assert snap.last_error == "tts crash"


def test_fail_active_sets_failed_state():
    backend = AsyncBackend()
    runtime = BookDiagnosticsTTSRuntimeCoordinator(
        gateway=BookDiagnosticsTTSGateway(backend=backend)
    )
    runtime.enqueue(_event())
    runtime.process_next()
    snap = runtime.fail_active("manual failure", event_id="voice-1")
    assert snap.state == "FAILED"
    assert runtime.snapshot().last_error == "manual failure"


def test_reset_clears_queue_session_and_runtime_status():
    runtime = BookDiagnosticsTTSRuntimeCoordinator()
    runtime.enqueue(_event())
    runtime.process_next()
    runtime.enqueue(_event("voice-2"))
    snap = runtime.reset()
    assert snap.queue_size == 0
    assert snap.session_state == "IDLE"
    assert snap.last_event_id is None
    assert snap.last_status is None
    assert snap.last_error is None


def test_rejects_decision_affecting_event_through_rc32():
    runtime = BookDiagnosticsTTSRuntimeCoordinator()
    with pytest.raises(PermissionError):
        runtime.enqueue(_event(affects_decision=True))
