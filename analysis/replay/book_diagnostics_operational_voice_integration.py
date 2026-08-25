"""
BookDiagnostics RC51 - Operational Voice Integration Contract.

Define a fronteira segura entre uma mensagem observacional ja aprovada e o
BookDiagnosticsVoiceService. A integracao exige RC50 operacionalmente pronto
antes de delegar qualquer mensagem para a cadeia de voz.

Esta camada permanece exclusivamente de apresentacao: nao interpreta mercado,
nao cria sinais e nunca modifica Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class OperationalVoiceDispatchResult:
    version: str
    accepted: bool
    dispatched: bool
    blocked: bool
    reason: str
    readiness_reason: str | None
    voice_result: object | None
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsOperationalVoiceIntegration:
    VERSION = "RC51-OPERATIONAL-VOICE-INTEGRATION"

    def __init__(self, *, voice_service):
        if voice_service is None:
            raise ValueError("voice_service is required")
        self.voice_service = voice_service

    def dispatch(self, message_decision) -> OperationalVoiceDispatchResult:
        """Despacha somente apos RC50 liberar explicitamente a voz operacional."""
        if message_decision is None:
            raise ValueError("message_decision is required")

        try:
            readiness = self.voice_service.require_operational_ready()
        except PermissionError as exc:
            reason = str(exc) or "VOICE_NOT_READY"
            return self._result(
                accepted=False,
                dispatched=False,
                blocked=True,
                reason="READINESS_BLOCKED",
                readiness_reason=reason,
                voice_result=None,
            )

        readiness_payload = self._payload(readiness)
        self._validate_readiness(readiness_payload)

        try:
            voice_result = self.voice_service.submit_and_process(message_decision)
        except RuntimeError as exc:
            return self._result(
                accepted=False,
                dispatched=False,
                blocked=True,
                reason="VOICE_SERVICE_UNAVAILABLE",
                readiness_reason=str(readiness_payload.get("reason", "READY")),
                voice_result=str(exc),
            )

        return self._result(
            accepted=True,
            dispatched=True,
            blocked=False,
            reason="DISPATCHED",
            readiness_reason=str(readiness_payload.get("reason", "READY")),
            voice_result=voice_result,
        )

    def check(self) -> OperationalVoiceDispatchResult:
        """Consulta a possibilidade de integracao sem despachar mensagem."""
        try:
            readiness = self.voice_service.require_operational_ready()
        except PermissionError as exc:
            return self._result(
                accepted=False,
                dispatched=False,
                blocked=True,
                reason="READINESS_BLOCKED",
                readiness_reason=str(exc) or "VOICE_NOT_READY",
                voice_result=None,
            )

        payload = self._payload(readiness)
        self._validate_readiness(payload)
        return self._result(
            accepted=True,
            dispatched=False,
            blocked=False,
            reason="READY",
            readiness_reason=str(payload.get("reason", "READY")),
            voice_result=None,
        )

    def _result(
        self,
        *,
        accepted: bool,
        dispatched: bool,
        blocked: bool,
        reason: str,
        readiness_reason: str | None,
        voice_result,
    ) -> OperationalVoiceDispatchResult:
        return OperationalVoiceDispatchResult(
            version=self.VERSION,
            accepted=bool(accepted),
            dispatched=bool(dispatched),
            blocked=bool(blocked),
            reason=str(reason),
            readiness_reason=readiness_reason,
            voice_result=voice_result,
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    @staticmethod
    def _validate_readiness(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC49-VOICE-READINESS-GATE":
            raise PermissionError("RC51 requires RC49 readiness contract")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid readiness contract")
        if not bool(payload.get("operational_voice_allowed", False)):
            raise PermissionError("RC51 requires operational_voice_allowed=True")
