"""
BookDiagnostics RC31 - Voice Event Contract.

Converte somente mensagens aprovadas pelo RC30 em eventos estruturados para
uma futura camada de voz. Nenhum evento fala por conta propria e nenhum campo
altera Strategy, Score, Risk, Decision ou Alert.

O perfil de voz e deliberadamente generico: assistente britanico sofisticado,
calmo, preciso e elegante. Nao representa nem clona uma voz identificavel de
ator ou personagem.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import math


@dataclass(slots=True, frozen=True)
class VoiceEventContract:
    version: str
    event_id: str
    text: str
    priority: str
    interrupt_allowed: bool
    estimated_duration_seconds: float
    voice_profile: str
    locale: str
    rate: float
    pitch: float
    volume: float
    source_fingerprint: str
    created_at: str
    readonly: bool = True
    affects_decision: bool = False
    requires_tts_adapter: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceEventFactory:
    VERSION = "RC31-VOICE-EVENT-CONTRACT"
    VOICE_PROFILE = "REFINED_BRITISH_AI_ASSISTANT"
    ALLOWED_PRIORITIES = {"NORMAL", "CAUTION", "URGENT"}

    def __init__(self, *, locale: str = "pt-BR", words_per_minute: int = 145):
        locale = str(locale or "").strip()
        if not locale:
            raise ValueError("locale is required")
        words_per_minute = int(words_per_minute)
        if words_per_minute < 80 or words_per_minute > 220:
            raise ValueError("words_per_minute must be between 80 and 220")
        self.locale = locale
        self.words_per_minute = words_per_minute

    def build(self, message_decision, *, now=None) -> VoiceEventContract:
        payload = (
            message_decision.to_dict()
            if hasattr(message_decision, "to_dict")
            else dict(message_decision or {})
        )
        self._validate_message(payload)

        text = str(payload.get("message", "") or "").strip()
        priority = str(payload.get("priority", "") or "").upper().strip()
        fingerprint = str(payload.get("fingerprint", "") or "").strip()
        created_at = self._iso_now(now)
        event_id = self._event_id(fingerprint, created_at, priority)
        duration = self._estimate_duration(text)
        rate, pitch, volume = self._prosody(priority)

        return VoiceEventContract(
            version=self.VERSION,
            event_id=event_id,
            text=text,
            priority=priority,
            interrupt_allowed=(priority == "URGENT"),
            estimated_duration_seconds=duration,
            voice_profile=self.VOICE_PROFILE,
            locale=self.locale,
            rate=rate,
            pitch=pitch,
            volume=volume,
            source_fingerprint=fingerprint,
            created_at=created_at,
        )

    @classmethod
    def _validate_message(cls, payload: dict):
        if str(payload.get("version", "") or "") != "RC30-ASSISTANT-MESSAGE-POLICY":
            raise PermissionError("RC31 requires RC30 message decision")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC31 requires readonly message")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC31 rejects decision-affecting message")
        if not bool(payload.get("should_emit", False)):
            raise PermissionError("RC31 only accepts RC30-approved messages")
        priority = str(payload.get("priority", "") or "").upper().strip()
        if priority not in cls.ALLOWED_PRIORITIES:
            raise ValueError("invalid voice priority")
        if not str(payload.get("message", "") or "").strip():
            raise ValueError("message text is required")
        if not str(payload.get("fingerprint", "") or "").strip():
            raise ValueError("source fingerprint is required")

    def _estimate_duration(self, text: str) -> float:
        words = max(1, len(text.split()))
        seconds = words / self.words_per_minute * 60.0
        return round(max(1.0, seconds), 2)

    @staticmethod
    def _prosody(priority: str) -> tuple[float, float, float]:
        if priority == "URGENT":
            return 1.03, -0.03, 1.0
        if priority == "CAUTION":
            return 0.97, -0.05, 0.94
        return 0.94, -0.06, 0.90

    @staticmethod
    def _event_id(fingerprint: str, created_at: str, priority: str) -> str:
        raw = f"{fingerprint}|{created_at}|{priority}".encode("utf-8")
        return "voice_" + hashlib.sha256(raw).hexdigest()[:20]

    @staticmethod
    def _iso_now(value) -> str:
        if value is None:
            return datetime.now(timezone.utc).isoformat()
        if isinstance(value, datetime):
            current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            return current.isoformat()
        text = str(value).strip()
        current = datetime.fromisoformat(text)
        if not current.tzinfo:
            current = current.replace(tzinfo=timezone.utc)
        return current.isoformat()
