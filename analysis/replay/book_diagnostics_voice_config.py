"""
BookDiagnostics RC40 - Voice Configuration Contract.

Centraliza configuracoes da camada de voz sem acoplar o sistema a um backend
real. O contrato e somente de apresentacao e nunca altera Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace


@dataclass(slots=True, frozen=True)
class VoiceConfig:
    version: str = "RC40-VOICE-CONFIGURATION-CONTRACT"
    enabled: bool = False
    backend: str = "NULL_TTS"
    language: str = "pt-BR"
    voice_profile: str = "BRITISH_CALM_PRECISE_ASSISTANT"
    speech_rate: float = 1.0
    allow_urgent_interrupt: bool = True
    queue_max_size: int = 12
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def with_updates(self, **changes) -> "VoiceConfig":
        updated = replace(self, **changes)
        validate_voice_config(updated)
        return updated


def validate_voice_config(value) -> VoiceConfig:
    payload = value.to_dict() if hasattr(value, "to_dict") else dict(value or {})

    if str(payload.get("version", "")) != "RC40-VOICE-CONFIGURATION-CONTRACT":
        raise PermissionError("RC40 requires RC40 voice configuration")
    if not bool(payload.get("readonly", False)):
        raise PermissionError("RC40 requires readonly configuration")
    if bool(payload.get("affects_decision", True)):
        raise PermissionError("RC40 rejects decision-affecting configuration")

    backend = str(payload.get("backend", "") or "").strip().upper()
    if not backend:
        raise ValueError("backend cannot be empty")

    language = str(payload.get("language", "") or "").strip()
    if not language:
        raise ValueError("language cannot be empty")

    voice_profile = str(payload.get("voice_profile", "") or "").strip()
    if not voice_profile:
        raise ValueError("voice_profile cannot be empty")

    speech_rate = float(payload.get("speech_rate", 0))
    if speech_rate < 0.5 or speech_rate > 2.0:
        raise ValueError("speech_rate must be between 0.5 and 2.0")

    queue_max_size = int(payload.get("queue_max_size", 0))
    if queue_max_size < 1 or queue_max_size > 100:
        raise ValueError("queue_max_size must be between 1 and 100")

    return VoiceConfig(
        enabled=bool(payload.get("enabled", False)),
        backend=backend,
        language=language,
        voice_profile=voice_profile,
        speech_rate=speech_rate,
        allow_urgent_interrupt=bool(payload.get("allow_urgent_interrupt", True)),
        queue_max_size=queue_max_size,
    )
