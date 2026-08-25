"""
BookDiagnostics RC34 - Voice Session Controller.

Controla apenas o estado de apresentacao da fala produzida pelo RC33.
Nao sintetiza audio, nao executa IO e nao altera Strategy, Score, Risk,
Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceSessionSnapshot:
    version: str
    state: str
    active_event_id: str | None
    active_priority: str | None
    interruptible: bool
    last_outcome: str | None
    error: str | None
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceSessionController:
    VERSION = "RC34-VOICE-SESSION-CONTROLLER"
    SOURCE_VERSION = "RC33-VOICE-OUTPUT-ADAPTER"
    VALID_STATES = {"IDLE", "SPEAKING", "FAILED"}

    def __init__(self):
        self._state = "IDLE"
        self._active = None
        self._last_outcome = None
        self._error = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_idle(self) -> bool:
        return self._state == "IDLE"

    @property
    def is_speaking(self) -> bool:
        return self._state == "SPEAKING"

    def start(self, command):
        payload = self._payload(command)
        self._validate_command(payload)

        if self.is_speaking:
            if not self._can_interrupt(payload):
                raise RuntimeError("active voice session cannot be interrupted")
            self._last_outcome = "INTERRUPTED"

        self._active = dict(payload)
        self._state = "SPEAKING"
        self._error = None
        return self.snapshot()

    def complete(self, *, event_id: str | None = None):
        self._require_active(event_id)
        self._last_outcome = "COMPLETED"
        self._active = None
        self._state = "IDLE"
        self._error = None
        return self.snapshot()

    def fail(self, error: str, *, event_id: str | None = None):
        self._require_active(event_id)
        message = str(error or "").strip()
        if not message:
            raise ValueError("error cannot be empty")
        self._last_outcome = "FAILED"
        self._active = None
        self._state = "FAILED"
        self._error = message
        return self.snapshot()

    def reset(self):
        self._active = None
        self._state = "IDLE"
        self._error = None
        return self.snapshot()

    def snapshot(self) -> VoiceSessionSnapshot:
        active = self._active or {}
        return VoiceSessionSnapshot(
            version=self.VERSION,
            state=self._state,
            active_event_id=active.get("event_id"),
            active_priority=active.get("priority"),
            interruptible=bool(active.get("interrupt", False)),
            last_outcome=self._last_outcome,
            error=self._error,
        )

    def _can_interrupt(self, incoming: dict) -> bool:
        if str(incoming.get("priority", "")).upper() != "URGENT":
            return False
        if not bool(incoming.get("interrupt", False)):
            return False
        if not self._active:
            return True
        return str(incoming.get("event_id")) != str(self._active.get("event_id"))

    def _require_active(self, event_id: str | None) -> None:
        if not self.is_speaking or not self._active:
            raise RuntimeError("no active voice session")
        if event_id is not None and str(event_id) != str(self._active.get("event_id")):
            raise RuntimeError("event_id does not match active voice session")

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate_command(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC34 requires RC33 voice output command")
        if str(payload.get("command", "")) != "SPEAK":
            raise ValueError("RC34 accepts only SPEAK commands")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC34 requires readonly voice command")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC34 rejects decision-affecting command")

        event_id = str(payload.get("event_id", "") or "").strip()
        if not event_id:
            raise ValueError("event_id cannot be empty")

        priority = str(payload.get("priority", "") or "").upper()
        if priority not in {"NORMAL", "CAUTION", "URGENT"}:
            raise ValueError("invalid voice priority")

        interrupt = bool(payload.get("interrupt", False))
        if interrupt and priority != "URGENT":
            raise ValueError("only URGENT command may interrupt")
