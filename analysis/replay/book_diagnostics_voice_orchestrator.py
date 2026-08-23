"""
BookDiagnostics RC53 - Voice Orchestrator.

Fachada observacional que recebe a projecao RC29, aplica a politica RC30 e
entrega a decisao ao adapter RC52/contrato RC51. Nao conecta automaticamente
ao app.main e nao altera Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_assistant_message_policy import (
    BookDiagnosticsAssistantMessagePolicy,
)
from analysis.replay.book_diagnostics_operational_voice_adapter import (
    BookDiagnosticsOperationalVoiceAdapter,
)
from analysis.replay.book_diagnostics_operational_voice_integration import (
    BookDiagnosticsOperationalVoiceIntegration,
)


@dataclass(slots=True, frozen=True)
class VoiceOrchestratorResult:
    version: str
    message_should_emit: bool
    priority: str
    message_reason: str
    dispatched: bool
    blocked: bool
    adapter_reason: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceOrchestrator:
    VERSION = "RC53-BOOK-DIAGNOSTICS-VOICE-ORCHESTRATOR"

    def __init__(self, *, voice_adapter, message_policy=None):
        if voice_adapter is None:
            raise ValueError("voice_adapter is required")
        self.voice_adapter = voice_adapter
        self.message_policy = message_policy or BookDiagnosticsAssistantMessagePolicy()

    @classmethod
    def from_voice_service(cls, voice_service, *, message_policy=None):
        if voice_service is None:
            raise ValueError("voice_service is required")
        integration = BookDiagnosticsOperationalVoiceIntegration(voice_service=voice_service)
        adapter = BookDiagnosticsOperationalVoiceAdapter(integration=integration)
        return cls(voice_adapter=adapter, message_policy=message_policy)

    def check(self, projection, *, now=None) -> VoiceOrchestratorResult:
        """Aplica RC30 e consulta RC52/RC51 sem despachar voz."""
        message_decision = self.message_policy.evaluate(projection, now=now)
        adapter_result = self.voice_adapter.check(message_decision)
        return self._result(message_decision, adapter_result)

    def dispatch(self, projection, *, now=None) -> VoiceOrchestratorResult:
        """Aplica RC30 e delega ao RC52 somente quando permitido."""
        message_decision = self.message_policy.evaluate(projection, now=now)
        adapter_result = self.voice_adapter.dispatch(message_decision)
        return self._result(message_decision, adapter_result)

    def reset(self):
        self.message_policy.reset()

    def _result(self, message_decision, adapter_result) -> VoiceOrchestratorResult:
        adapter_payload = self._payload(adapter_result)
        self._validate_adapter(adapter_payload)
        return VoiceOrchestratorResult(
            version=self.VERSION,
            message_should_emit=bool(message_decision.should_emit),
            priority=str(message_decision.priority),
            message_reason=str(message_decision.reason),
            dispatched=bool(adapter_payload.get("dispatched", False)),
            blocked=bool(adapter_payload.get("blocked", False)),
            adapter_reason=str(adapter_payload.get("reason", "UNKNOWN")),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    @staticmethod
    def _validate_adapter(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC52-OPERATIONAL-VOICE-ADAPTER":
            raise PermissionError("RC53 requires RC52 adapter result")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC52 adapter result")
