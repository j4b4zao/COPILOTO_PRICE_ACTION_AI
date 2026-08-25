"""
BookDiagnostics RC52 - Operational Voice Adapter.

Adapta decisoes reais RC30 ja aprovadas para a fronteira operacional RC51.
Nao interpreta mercado, nao cria sinais e nao conecta automaticamente voz ao bot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class OperationalVoiceAdapterResult:
    version: str
    accepted: bool
    dispatched: bool
    suppressed: bool
    blocked: bool
    priority: str
    reason: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsOperationalVoiceAdapter:
    VERSION = "RC52-OPERATIONAL-VOICE-ADAPTER"
    SOURCE_VERSION = "RC30-ASSISTANT-MESSAGE-POLICY"
    INTEGRATION_VERSION = "RC51-OPERATIONAL-VOICE-INTEGRATION"

    def __init__(self, *, integration):
        if integration is None:
            raise ValueError("integration is required")
        self.integration = integration

    def check(self, message_decision) -> OperationalVoiceAdapterResult:
        payload = self._payload(message_decision)
        self._validate_message(payload)
        priority = str(payload["priority"]).upper()

        if not bool(payload.get("should_emit", False)):
            return self._result(False, False, True, False, priority, str(payload.get("reason", "SUPPRESSED") or "SUPPRESSED"))

        result = self.integration.check()
        out = self._payload(result)
        self._validate_integration(out)
        return self._result(
            bool(out.get("accepted", False)),
            False,
            False,
            bool(out.get("blocked", False)),
            priority,
            str(out.get("reason", "READY")),
        )

    def dispatch(self, message_decision) -> OperationalVoiceAdapterResult:
        payload = self._payload(message_decision)
        self._validate_message(payload)
        priority = str(payload["priority"]).upper()

        if not bool(payload.get("should_emit", False)):
            return self._result(False, False, True, False, priority, str(payload.get("reason", "SUPPRESSED") or "SUPPRESSED"))

        result = self.integration.dispatch(message_decision)
        out = self._payload(result)
        self._validate_integration(out)
        return self._result(
            bool(out.get("accepted", False)),
            bool(out.get("dispatched", False)),
            False,
            bool(out.get("blocked", False)),
            priority,
            str(out.get("reason", "BLOCKED")),
        )

    def _result(self, accepted, dispatched, suppressed, blocked, priority, reason):
        return OperationalVoiceAdapterResult(
            version=self.VERSION,
            accepted=bool(accepted),
            dispatched=bool(dispatched),
            suppressed=bool(suppressed),
            blocked=bool(blocked),
            priority=str(priority),
            reason=str(reason),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate_message(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC52 requires RC30 assistant message decision")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC52 requires readonly RC30 decision")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC52 rejects decision-affecting input")

        priority = str(payload.get("priority", "") or "").upper()
        if priority not in {"NORMAL", "CAUTION", "URGENT"}:
            raise ValueError("invalid message priority")
        if bool(payload.get("should_emit", False)) and not str(payload.get("message", "") or "").strip():
            raise ValueError("approved RC30 message cannot be empty")

    def _validate_integration(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.INTEGRATION_VERSION:
            raise PermissionError("RC52 requires RC51 integration result")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC51 integration result")
