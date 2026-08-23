"""
BookDiagnostics RC37 - Runtime Event Bridge.

Liga a decisao de mensagem RC30 ao contrato de evento RC31 e ao runtime RC36.
A ponte corrige explicitamente a diferenca de nomes entre RC30
(should_emit/message) e RC31 (approved/text), sem alterar Strategy, Score,
Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_voice_event import BookDiagnosticsVoiceEventFactory
from analysis.replay.book_diagnostics_tts_runtime import BookDiagnosticsTTSRuntimeCoordinator


@dataclass(slots=True, frozen=True)
class RuntimeBridgeDecision:
    version: str
    accepted: bool
    emitted: bool
    event_id: str | None
    priority: str | None
    reason: str
    queue_size: int
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsRuntimeEventBridge:
    VERSION = "RC37-RUNTIME-EVENT-BRIDGE"
    SOURCE_VERSION = "RC30-ASSISTANT-MESSAGE-POLICY"

    def __init__(self, *, factory=None, runtime=None):
        self.factory = factory or BookDiagnosticsVoiceEventFactory()
        self.runtime = runtime or BookDiagnosticsTTSRuntimeCoordinator()

    def submit(self, message_decision) -> RuntimeBridgeDecision:
        payload = self._payload(message_decision)
        self._validate(payload)

        priority = str(payload.get("priority", "NORMAL") or "NORMAL").upper()
        if not bool(payload.get("should_emit", False)):
            return RuntimeBridgeDecision(
                version=self.VERSION,
                accepted=False,
                emitted=False,
                event_id=None,
                priority=priority,
                reason=str(payload.get("reason", "SUPPRESSED") or "SUPPRESSED"),
                queue_size=self.runtime.snapshot().queue_size,
            )

        rc31_payload = {
            "version": self.SOURCE_VERSION,
            "approved": True,
            "text": str(payload.get("message", "") or "").strip(),
            "priority": priority,
            "readonly": True,
            "affects_decision": False,
        }
        event = self.factory.build(rc31_payload)
        queue_decision = self.runtime.enqueue(event)

        return RuntimeBridgeDecision(
            version=self.VERSION,
            accepted=bool(queue_decision.accepted),
            emitted=True,
            event_id=event.event_id,
            priority=priority,
            reason=str(queue_decision.reason),
            queue_size=int(queue_decision.queue_size),
        )

    def submit_and_process(self, message_decision):
        decision = self.submit(message_decision)
        if not decision.accepted:
            return decision, None
        return decision, self.runtime.process_next()

    def snapshot(self):
        return self.runtime.snapshot()

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "") or "") != self.SOURCE_VERSION:
            raise PermissionError("RC37 requires RC30 assistant message decision")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC37 requires readonly RC30 decision")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC37 rejects decision-affecting input")
        priority = str(payload.get("priority", "") or "").upper()
        if priority not in {"NORMAL", "CAUTION", "URGENT"}:
            raise ValueError("invalid message priority")
        if bool(payload.get("should_emit", False)) and not str(payload.get("message", "") or "").strip():
            raise ValueError("approved RC30 message cannot be empty")
