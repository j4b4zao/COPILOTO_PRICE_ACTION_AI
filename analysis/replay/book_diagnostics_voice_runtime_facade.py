"""
BookDiagnostics RC38 - Voice Runtime Facade.

Expoe uma API unica e estavel para consumir toda a cadeia de voz do
BookDiagnostics sem exigir conhecimento direto de RC31-RC37. A fachada
permanece observacional e nao altera Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_runtime_event_bridge import (
    BookDiagnosticsRuntimeEventBridge,
)


@dataclass(slots=True, frozen=True)
class VoiceRuntimeFacadeSnapshot:
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


class BookDiagnosticsVoiceRuntimeFacade:
    VERSION = "RC38-VOICE-RUNTIME-FACADE"

    def __init__(self, *, bridge: BookDiagnosticsRuntimeEventBridge | None = None):
        self.bridge = bridge or BookDiagnosticsRuntimeEventBridge()

    @property
    def runtime(self):
        return self.bridge.runtime

    def submit_message(self, message_decision):
        """Recebe uma decisao RC30 e apenas tenta enfileira-la."""
        return self.bridge.submit(message_decision)

    def submit_and_process(self, message_decision):
        """Recebe RC30, enfileira e tenta processar imediatamente."""
        return self.bridge.submit_and_process(message_decision)

    def process_next(self):
        """Processa o proximo evento ja presente na fila."""
        return self.runtime.process_next()

    def complete_active(self, *, event_id: str | None = None):
        return self.runtime.complete_active(event_id=event_id)

    def fail_active(self, error: str, *, event_id: str | None = None):
        return self.runtime.fail_active(error, event_id=event_id)

    def stop_active(self) -> bool:
        return self.runtime.stop_active()

    def reset(self) -> VoiceRuntimeFacadeSnapshot:
        self.runtime.reset()
        return self.snapshot()

    def snapshot(self) -> VoiceRuntimeFacadeSnapshot:
        current = self.bridge.snapshot()
        payload = current.to_dict() if hasattr(current, "to_dict") else dict(current or {})
        self._validate_runtime_snapshot(payload)
        return VoiceRuntimeFacadeSnapshot(
            version=self.VERSION,
            queue_size=int(payload["queue_size"]),
            session_state=str(payload["session_state"]),
            active_event_id=payload.get("active_event_id"),
            backend=str(payload["backend"]),
            backend_healthy=bool(payload["backend_healthy"]),
            last_event_id=payload.get("last_event_id"),
            last_status=payload.get("last_status"),
            last_error=payload.get("last_error"),
        )

    @staticmethod
    def _validate_runtime_snapshot(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC36-TTS-RUNTIME-COORDINATOR":
            raise PermissionError("RC38 requires RC36 runtime snapshot")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC38 requires readonly runtime snapshot")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC38 rejects decision-affecting runtime snapshot")
        if int(payload.get("queue_size", -1)) < 0:
            raise ValueError("queue_size cannot be negative")
        if str(payload.get("session_state", "")) not in {"IDLE", "SPEAKING", "FAILED"}:
            raise ValueError("invalid session_state")
        if not str(payload.get("backend", "") or "").strip():
            raise ValueError("backend cannot be empty")
