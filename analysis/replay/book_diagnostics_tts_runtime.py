"""
BookDiagnostics RC36 - TTS Runtime Coordinator.

Integra RC32 (fila), RC33 (comando), RC34 (sessao) e RC35 (gateway TTS)
em um fluxo unico de runtime, sem alterar Strategy, Score, Risk, Decision
ou Alert. O backend padrao continua sendo o NullTTSBackend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_tts_backend import BookDiagnosticsTTSGateway
from analysis.replay.book_diagnostics_voice_output import BookDiagnosticsVoiceOutputAdapter
from analysis.replay.book_diagnostics_voice_queue import BookDiagnosticsVoiceQueue
from analysis.replay.book_diagnostics_voice_session import BookDiagnosticsVoiceSessionController


@dataclass(slots=True, frozen=True)
class TTSRuntimeSnapshot:
    version: str
    queue_size: int
    session_state: str
    active_event_id: str | None
    backend: str
    backend_healthy: bool
    last_event_id: str | None
    last_status: str | None
    last_error: str | None
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsTTSRuntimeCoordinator:
    VERSION = "RC36-TTS-RUNTIME-COORDINATOR"

    def __init__(
        self,
        *,
        queue: BookDiagnosticsVoiceQueue | None = None,
        adapter: BookDiagnosticsVoiceOutputAdapter | None = None,
        session: BookDiagnosticsVoiceSessionController | None = None,
        gateway: BookDiagnosticsTTSGateway | None = None,
    ):
        self.queue = queue or BookDiagnosticsVoiceQueue()
        self.adapter = adapter or BookDiagnosticsVoiceOutputAdapter()
        self.session = session or BookDiagnosticsVoiceSessionController()
        self.gateway = gateway or BookDiagnosticsTTSGateway()
        self._last_event_id = None
        self._last_status = None
        self._last_error = None

    def enqueue(self, voice_event):
        return self.queue.enqueue(voice_event)

    def process_next(self):
        event = self.queue.peek_next()
        if event is None:
            self._last_status = "EMPTY"
            self._last_error = None
            return None

        command = self.adapter.prepare(event)

        if self.session.is_speaking:
            if not bool(command.interrupt):
                self._last_status = "BUSY"
                self._last_error = None
                return None

            active_id = self.session.snapshot().active_event_id
            if active_id:
                self.gateway.stop(active_id)

        event = self.queue.pop_next()
        command = self.adapter.prepare(event)
        self.session.start(command)
        self._last_event_id = command.event_id

        try:
            result = self.gateway.speak(command)
        except Exception as exc:
            self.session.fail(str(exc), event_id=command.event_id)
            self._last_status = "FAILED"
            self._last_error = str(exc)
            raise

        if result.error:
            self.session.fail(result.error, event_id=command.event_id)
            self._last_status = "FAILED"
            self._last_error = result.error
            return result

        if result.completed:
            self.session.complete(event_id=command.event_id)
            self._last_status = "COMPLETED"
        elif result.accepted:
            self._last_status = "SPEAKING"
        else:
            self.session.fail("tts backend rejected command", event_id=command.event_id)
            self._last_status = "FAILED"
            self._last_error = "tts backend rejected command"

        if self._last_status != "FAILED":
            self._last_error = None

        return result

    def complete_active(self, *, event_id: str | None = None):
        snap = self.session.complete(event_id=event_id)
        self._last_status = "COMPLETED"
        self._last_error = None
        return snap

    def fail_active(self, error: str, *, event_id: str | None = None):
        snap = self.session.fail(error, event_id=event_id)
        self._last_status = "FAILED"
        self._last_error = str(error)
        return snap

    def stop_active(self) -> bool:
        snap = self.session.snapshot()
        if snap.active_event_id is None:
            return False
        stopped = self.gateway.stop(snap.active_event_id)
        self.session.complete(event_id=snap.active_event_id)
        self._last_status = "STOPPED"
        self._last_error = None
        return bool(stopped)

    def reset(self):
        self.queue.clear()
        self.session.reset()
        self._last_event_id = None
        self._last_status = None
        self._last_error = None
        return self.snapshot()

    def snapshot(self) -> TTSRuntimeSnapshot:
        session = self.session.snapshot()
        return TTSRuntimeSnapshot(
            version=self.VERSION,
            queue_size=len(self.queue),
            session_state=session.state,
            active_event_id=session.active_event_id,
            backend=self.gateway.backend_name(),
            backend_healthy=self.gateway.healthcheck(),
            last_event_id=self._last_event_id,
            last_status=self._last_status,
            last_error=self._last_error,
        )
