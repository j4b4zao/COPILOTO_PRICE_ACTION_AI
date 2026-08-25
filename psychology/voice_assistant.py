"""Ponte controlada entre CoachingEngine e voz (RC4)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.coaching_engine import CoachingResult


@dataclass(frozen=True, slots=True)
class VoiceAssistantConfig:
    enabled: bool = False
    maximum_messages_per_dispatch: int = 2
    speak_guidance: bool = True
    speak_pause_recommendation: bool = True

    def __post_init__(self):
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled deve ser booleano.")
        if not 1 <= self.maximum_messages_per_dispatch <= 3:
            raise ValueError(
                "maximum_messages_per_dispatch deve ficar entre 1 e 3."
            )
        if not isinstance(self.speak_guidance, bool):
            raise TypeError("speak_guidance deve ser booleano.")
        if not isinstance(self.speak_pause_recommendation, bool):
            raise TypeError(
                "speak_pause_recommendation deve ser booleano."
            )


@dataclass(frozen=True, slots=True)
class VoiceDelivery:
    code: str
    priority: str
    status: str


@dataclass(frozen=True, slots=True)
class VoiceAssistantResult:
    status: str
    deliveries: tuple[VoiceDelivery, ...]
    attempted_count: int
    delivered_count: int
    failed_count: int
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class NullPsychologyVoiceSink:
    """Sink padrão seguro: valida a chamada sem produzir áudio."""

    name = "NULL_PSYCHOLOGY_VOICE"

    def speak(self, *, text, priority, code):
        if not str(text).strip():
            raise ValueError("text não pode ser vazio.")
        if priority not in {"NORMAL", "CAUTION", "URGENT"}:
            raise ValueError("priority inválida.")
        if not str(code).strip():
            raise ValueError("code não pode ser vazio.")
        return True


class VoiceAssistant:
    """Entrega coaching à voz; falhas são isoladas do fluxo operacional."""

    NAME = "VoiceAssistant"
    VERSION = "RC4"

    def __init__(self, *, config=None, sink=None):
        self.config = config or VoiceAssistantConfig()
        self.sink = sink or NullPsychologyVoiceSink()
        if not callable(getattr(self.sink, "speak", None)):
            raise TypeError("sink deve expor speak().")
        self.last_result = VoiceAssistantResult(
            status="DISABLED" if not self.config.enabled else "NOT_RUN",
            deliveries=(),
            attempted_count=0,
            delivered_count=0,
            failed_count=0,
        )

    def dispatch(self, coaching_result):
        if not isinstance(coaching_result, CoachingResult):
            raise TypeError("coaching_result incompatível.")

        if not self.config.enabled:
            return self._finish("DISABLED", ())

        selected = [
            message
            for message in coaching_result.messages
            if message.voice_candidate and self._allowed(message.code)
        ][: self.config.maximum_messages_per_dispatch]

        if not selected:
            return self._finish("SILENT", ())

        deliveries = []
        for message in selected:
            priority = self._priority(message.code)
            try:
                accepted = bool(self.sink.speak(
                    text=message.text,
                    priority=priority,
                    code=message.code,
                ))
            except Exception:
                deliveries.append(VoiceDelivery(
                    code=message.code,
                    priority=priority,
                    status="FAILED",
                ))
                continue
            deliveries.append(VoiceDelivery(
                code=message.code,
                priority=priority,
                status="DELIVERED" if accepted else "REJECTED",
            ))

        failed = sum(
            item.status in {"FAILED", "REJECTED"}
            for item in deliveries
        )
        if failed == 0:
            status = "DELIVERED"
        elif failed == len(deliveries):
            status = "FAILED"
        else:
            status = "PARTIAL"
        return self._finish(status, tuple(deliveries))

    def _allowed(self, code):
        if code == "PAUSE_RECOMMENDED":
            return self.config.speak_pause_recommendation
        return self.config.speak_guidance

    @staticmethod
    def _priority(code):
        if code == "PAUSE_RECOMMENDED":
            return "URGENT"
        if code in {
            "REVENGE_TRADING",
            "STOP_SEQUENCE",
            "OUTSIDE_PLAN",
            "OVERTRADING",
            "RUSHED_REENTRY",
        }:
            return "CAUTION"
        return "NORMAL"

    def _finish(self, status, deliveries):
        delivered = sum(
            item.status == "DELIVERED" for item in deliveries
        )
        failed = len(deliveries) - delivered
        self.last_result = VoiceAssistantResult(
            status=status,
            deliveries=tuple(deliveries),
            attempted_count=len(deliveries),
            delivered_count=delivered,
            failed_count=failed,
        )
        return self.last_result
