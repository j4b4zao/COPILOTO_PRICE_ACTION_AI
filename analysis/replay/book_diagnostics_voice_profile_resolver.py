"""
BookDiagnostics RC42 - Voice Profile Resolver.

Resolve language, voice_profile e speech_rate do RC40 para um perfil efetivo
consumido pelo RC31. A camada continua somente apresentacional e nao altera
Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_voice_config import VoiceConfig, validate_voice_config


@dataclass(slots=True, frozen=True)
class ResolvedVoiceProfile:
    version: str
    language: str
    voice_profile: str
    speech_rate: float
    words_per_minute: int
    allow_urgent_interrupt: bool
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceProfileResolver:
    VERSION = "RC42-VOICE-PROFILE-RESOLVER"
    BASE_WORDS_PER_MINUTE = 145

    def resolve(self, config: VoiceConfig | dict) -> ResolvedVoiceProfile:
        current = validate_voice_config(config)
        words_per_minute = round(self.BASE_WORDS_PER_MINUTE * current.speech_rate)
        words_per_minute = max(90, min(220, words_per_minute))

        return ResolvedVoiceProfile(
            version=self.VERSION,
            language=current.language,
            voice_profile=current.voice_profile,
            speech_rate=current.speech_rate,
            words_per_minute=words_per_minute,
            allow_urgent_interrupt=current.allow_urgent_interrupt,
        )


def validate_resolved_voice_profile(value) -> ResolvedVoiceProfile:
    payload = value.to_dict() if hasattr(value, "to_dict") else dict(value or {})

    if str(payload.get("version", "")) != "RC42-VOICE-PROFILE-RESOLVER":
        raise PermissionError("RC42 requires RC42 resolved voice profile")
    if not bool(payload.get("readonly", False)):
        raise PermissionError("RC42 requires readonly profile")
    if bool(payload.get("affects_decision", True)):
        raise PermissionError("RC42 rejects decision-affecting profile")

    language = str(payload.get("language", "") or "").strip()
    voice_profile = str(payload.get("voice_profile", "") or "").strip()
    speech_rate = float(payload.get("speech_rate", 0))
    words_per_minute = int(payload.get("words_per_minute", 0))

    if not language:
        raise ValueError("language cannot be empty")
    if not voice_profile:
        raise ValueError("voice_profile cannot be empty")
    if speech_rate < 0.5 or speech_rate > 2.0:
        raise ValueError("speech_rate must be between 0.5 and 2.0")
    if words_per_minute < 90 or words_per_minute > 220:
        raise ValueError("words_per_minute must be between 90 and 220")

    return ResolvedVoiceProfile(
        version="RC42-VOICE-PROFILE-RESOLVER",
        language=language,
        voice_profile=voice_profile,
        speech_rate=speech_rate,
        words_per_minute=words_per_minute,
        allow_urgent_interrupt=bool(payload.get("allow_urgent_interrupt", True)),
    )
