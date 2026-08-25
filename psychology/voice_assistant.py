"""Ponte controlada entre CoachingEngine e voz (RC4)."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time

from psychology.coaching_engine import CoachingResult


@dataclass(frozen=True, slots=True)
class VoiceAssistantConfig:
    enabled: bool = False
    maximum_messages_per_dispatch: int = 2
    speak_guidance: bool = True
    speak_pause_recommendation: bool = True
    cooldown_seconds: float = 60.0
    maximum_remembered_messages: int = 128

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
        if (
            isinstance(self.cooldown_seconds, bool)
            or not isinstance(self.cooldown_seconds, (int, float))
            or not math.isfinite(float(self.cooldown_seconds))
            or float(self.cooldown_seconds) < 0.0
        ):
            raise ValueError(
                "cooldown_seconds deve ser finito e não negativo."
            )
        if (
            isinstance(self.maximum_remembered_messages, bool)
            or not isinstance(self.maximum_remembered_messages, int)
        ):
            raise TypeError(
                "maximum_remembered_messages deve ser inteiro."
            )
        if not 1 <= self.maximum_remembered_messages <= 1000:
            raise ValueError(
                "maximum_remembered_messages deve ficar entre 1 e 1000."
            )


@dataclass(frozen=True, slots=True)
class VoiceDelivery:
    code: str
    priority: str
    status: str
    evidence_linked: bool = False
    evidence_audit_sequences: tuple[int, ...] = ()
    evidence_trade_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VoiceAssistantResult:
    status: str
    deliveries: tuple[VoiceDelivery, ...]
    attempted_count: int
    delivered_count: int
    failed_count: int
    suppressed_count: int = 0
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
    VERSION = "RC16"

    def __init__(self, *, config=None, sink=None, clock=None):
        self.config = config or VoiceAssistantConfig()
        self.sink = sink or NullPsychologyVoiceSink()
        self.clock = clock or time.monotonic
        if not callable(getattr(self.sink, "speak", None)):
            raise TypeError("sink deve expor speak().")
        if not callable(self.clock):
            raise TypeError("clock deve ser chamável.")
        self._delivered_at = {}
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
        now = self._now()
        for message in selected:
            priority = self._priority(message.code)
            key = (message.code, message.text)
            if self._in_cooldown(key, now):
                deliveries.append(VoiceDelivery(
                    code=message.code,
                    priority=priority,
                    status="COOLDOWN_SUPPRESSED",
                ))
                continue
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
            delivery_status = "DELIVERED" if accepted else "REJECTED"
            deliveries.append(VoiceDelivery(
                code=message.code,
                priority=priority,
                status=delivery_status,
            ))
            if accepted:
                self._remember(key, now)

        failed = sum(
            item.status in {"FAILED", "REJECTED"}
            for item in deliveries
        )
        suppressed = sum(
            item.status == "COOLDOWN_SUPPRESSED"
            for item in deliveries
        )
        delivered = sum(
            item.status == "DELIVERED"
            for item in deliveries
        )
        if suppressed == len(deliveries):
            status = "COOLDOWN"
        elif failed and not delivered:
            status = "FAILED"
        elif failed or suppressed:
            status = "PARTIAL"
        else:
            status = "DELIVERED"
        return self._finish(status, tuple(deliveries))

    def _now(self):
        value = self.clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("clock deve retornar número.")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("clock deve retornar valor finito.")
        return value

    def _in_cooldown(self, key, now):
        delivered_at = self._delivered_at.get(key)
        if delivered_at is None:
            return False
        return (
            now - delivered_at
            < float(self.config.cooldown_seconds)
        )

    def _remember(self, key, now):
        self._delivered_at[key] = now
        while (
            len(self._delivered_at)
            > self.config.maximum_remembered_messages
        ):
            oldest = min(
                self._delivered_at,
                key=self._delivered_at.get,
            )
            del self._delivered_at[oldest]

    def clear_cooldown(self):
        self._delivered_at.clear()

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
        failed = sum(
            item.status in {"FAILED", "REJECTED"}
            for item in deliveries
        )
        suppressed = sum(
            item.status == "COOLDOWN_SUPPRESSED"
            for item in deliveries
        )
        attempted = delivered + failed
        self.last_result = VoiceAssistantResult(
            status=status,
            deliveries=tuple(deliveries),
            attempted_count=attempted,
            delivered_count=delivered,
            failed_count=failed,
            suppressed_count=suppressed,
        )
        return self.last_result
