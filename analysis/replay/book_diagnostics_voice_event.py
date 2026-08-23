"""
BookDiagnostics RC31/RC42 - Voice Event Contract.

Converte somente mensagens aprovadas pelo RC30 em eventos estruturados de voz.
RC42 permite que idioma, perfil, velocidade e politica de interrupcao venham
do VoiceConfig, preservando o perfil padrao quando nenhum resolver e injetado.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_profile_resolver import (
    BookDiagnosticsVoiceProfileResolver,
    ResolvedVoiceProfile,
    validate_resolved_voice_profile,
)


@dataclass(slots=True, frozen=True)
class VoiceEvent:
    version: str
    event_id: str
    text: str
    priority: str
    interrupt_allowed: bool
    estimated_duration_seconds: float
    voice_profile: str
    language: str
    speech_rate: float
    source_version: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceEventFactory:
    VERSION = "RC31-VOICE-EVENT-CONTRACT"
    SOURCE_VERSION = "RC30-ASSISTANT-MESSAGE-POLICY"

    def __init__(self, *, profile: ResolvedVoiceProfile | None = None):
        resolved = profile or BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig())
        self.profile = validate_resolved_voice_profile(resolved)

    def build(self, approved_message) -> VoiceEvent:
        payload = self._payload(approved_message)
        self._validate(payload)
        text = str(payload.get("text", "") or "").strip()
        priority = str(payload.get("priority", "NORMAL") or "NORMAL").upper()
        event_id = self._event_id(text=text, priority=priority)
        return VoiceEvent(
            version=self.VERSION,
            event_id=event_id,
            text=text,
            priority=priority,
            interrupt_allowed=(priority == "URGENT" and self.profile.allow_urgent_interrupt),
            estimated_duration_seconds=self._estimate_duration(text),
            voice_profile=self.profile.voice_profile,
            language=self.profile.language,
            speech_rate=self.profile.speech_rate,
            source_version=self.SOURCE_VERSION,
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict):
        if str(payload.get("version", "") or "") != self.SOURCE_VERSION:
            raise PermissionError("RC31 requires RC30 approved message")
        if not bool(payload.get("approved", False)):
            raise PermissionError("RC31 rejects suppressed RC30 message")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC31 requires readonly message")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC31 rejects decision-affecting message")
        text = str(payload.get("text", "") or "").strip()
        if not text:
            raise ValueError("voice event text cannot be empty")
        priority = str(payload.get("priority", "") or "").upper()
        if priority not in {"NORMAL", "CAUTION", "URGENT"}:
            raise ValueError("invalid voice priority")

    def _estimate_duration(self, text: str) -> float:
        words = max(1, len(text.split()))
        seconds = words / self.profile.words_per_minute * 60.0
        return round(max(1.0, seconds), 2)

    @staticmethod
    def _event_id(*, text: str, priority: str) -> str:
        digest = sha256(f"{priority}|{text}".encode("utf-8")).hexdigest()[:16]
        return f"voice-{digest}"
