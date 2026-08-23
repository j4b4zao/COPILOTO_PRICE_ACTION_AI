"""
BookDiagnostics RC45 - Voice Capability / Diagnostics.

Inspeciona configuracao, registry, backend e capacidade de voz sem iniciar fala.
Permanece somente na camada de apresentacao e nunca altera Strategy, Score,
Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_tts_backend_registry import (
    BookDiagnosticsTTSBackendRegistry,
    get_default_tts_backend_registry,
)
from analysis.replay.book_diagnostics_voice_config import VoiceConfig, validate_voice_config


@dataclass(slots=True, frozen=True)
class VoiceCapabilitySnapshot:
    version: str
    enabled: bool
    configured_backend: str
    backend_registered: bool
    backend_instantiable: bool
    backend_healthy: bool
    language: str
    voice_profile: str
    speech_rate: float
    available_voice_count: int
    selected_voice: str | None
    selection_reason: str | None
    ready_for_real_audio: bool
    error: str | None
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceDiagnostics:
    VERSION = "RC45-VOICE-CAPABILITY-DIAGNOSTICS"

    def __init__(
        self,
        *,
        config: VoiceConfig | None = None,
        backend_registry: BookDiagnosticsTTSBackendRegistry | None = None,
    ):
        self.config = validate_voice_config(config or VoiceConfig())
        self.backend_registry = backend_registry or get_default_tts_backend_registry()

    def inspect(self) -> VoiceCapabilitySnapshot:
        backend_name = self.config.backend
        registered = self.backend_registry.contains(backend_name)
        if not registered:
            return self._snapshot(
                backend_registered=False,
                backend_instantiable=False,
                backend_healthy=False,
                error=f"unknown TTS backend: {backend_name}",
            )

        try:
            backend = self.backend_registry.create(backend_name)
        except Exception as exc:
            return self._snapshot(
                backend_registered=True,
                backend_instantiable=False,
                backend_healthy=False,
                error=str(exc),
            )

        try:
            healthy = bool(backend.healthcheck())
        except Exception as exc:
            return self._snapshot(
                backend_registered=True,
                backend_instantiable=True,
                backend_healthy=False,
                error=f"healthcheck failed: {exc}",
            )

        voices = ()
        selected_voice = None
        selection_reason = None

        if callable(getattr(backend, "available_voices", None)):
            try:
                voices = tuple(backend.available_voices() or ())
            except Exception as exc:
                return self._snapshot(
                    backend_registered=True,
                    backend_instantiable=True,
                    backend_healthy=healthy,
                    error=f"voice discovery failed: {exc}",
                )

        if callable(getattr(backend, "select_voice", None)):
            try:
                selection = backend.select_voice(
                    voice_profile=self.config.voice_profile,
                    language=self.config.language,
                )
                selected_voice = getattr(selection, "selected_voice", None)
                selection_reason = getattr(selection, "reason", None)
            except Exception as exc:
                return self._snapshot(
                    backend_registered=True,
                    backend_instantiable=True,
                    backend_healthy=healthy,
                    available_voice_count=len(voices),
                    error=f"voice selection failed: {exc}",
                )

        real_backend = backend_name != "NULL_TTS"
        ready = bool(self.config.enabled and real_backend and healthy)
        if callable(getattr(backend, "select_voice", None)):
            ready = ready and bool(selected_voice)

        return self._snapshot(
            backend_registered=True,
            backend_instantiable=True,
            backend_healthy=healthy,
            available_voice_count=len(voices),
            selected_voice=selected_voice,
            selection_reason=selection_reason,
            ready_for_real_audio=ready,
            error=None,
        )

    def _snapshot(
        self,
        *,
        backend_registered: bool,
        backend_instantiable: bool,
        backend_healthy: bool,
        available_voice_count: int = 0,
        selected_voice: str | None = None,
        selection_reason: str | None = None,
        ready_for_real_audio: bool = False,
        error: str | None = None,
    ) -> VoiceCapabilitySnapshot:
        return VoiceCapabilitySnapshot(
            version=self.VERSION,
            enabled=self.config.enabled,
            configured_backend=self.config.backend,
            backend_registered=backend_registered,
            backend_instantiable=backend_instantiable,
            backend_healthy=backend_healthy,
            language=self.config.language,
            voice_profile=self.config.voice_profile,
            speech_rate=self.config.speech_rate,
            available_voice_count=int(available_voice_count),
            selected_voice=selected_voice,
            selection_reason=selection_reason,
            ready_for_real_audio=bool(ready_for_real_audio),
            error=error,
        )
