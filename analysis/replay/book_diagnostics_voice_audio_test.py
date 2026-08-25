"""
BookDiagnostics RC47 - Controlled Real Audio Test Contract.

Fornece um teste explicito, curto e isolado de audio real. O teste somente pode
executar quando o diagnostico RC45 confirma `ready_for_real_audio=True`.
Nunca e disparado automaticamente pelo bot e permanece fora do nucleo
Strategy -> Score -> Risk -> Decision -> Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_tts_backend import BookDiagnosticsTTSGateway
from analysis.replay.book_diagnostics_voice_diagnostics import BookDiagnosticsVoiceDiagnostics
from analysis.replay.book_diagnostics_voice_output import VoiceOutputCommand


@dataclass(slots=True, frozen=True)
class ControlledAudioTestResult:
    version: str
    attempted: bool
    executed: bool
    backend: str
    selected_voice: str | None
    text: str
    accepted: bool
    completed: bool
    error: str | None
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsControlledAudioTest:
    VERSION = "RC47-CONTROLLED-REAL-AUDIO-TEST"
    DEFAULT_TEXT = "Teste de voz do Copiloto Price Action AI."

    def __init__(self, *, config, backend_registry, diagnostics=None):
        self.config = config
        self.backend_registry = backend_registry
        self.diagnostics = diagnostics or BookDiagnosticsVoiceDiagnostics(
            config=config,
            backend_registry=backend_registry,
        )

    def run(self, *, text: str | None = None) -> ControlledAudioTestResult:
        phrase = str(text or self.DEFAULT_TEXT).strip()
        if not phrase:
            raise ValueError("audio test text cannot be empty")
        if len(phrase) > 160:
            raise ValueError("audio test text must be at most 160 characters")

        capability = self.diagnostics.inspect()
        if not capability.ready_for_real_audio:
            return ControlledAudioTestResult(
                version=self.VERSION,
                attempted=True,
                executed=False,
                backend=capability.configured_backend,
                selected_voice=capability.selected_voice,
                text=phrase,
                accepted=False,
                completed=False,
                error=capability.error or "voice diagnostics not ready for real audio",
            )

        try:
            backend = self.backend_registry.create(capability.configured_backend)
            gateway = BookDiagnosticsTTSGateway(backend=backend)
            command = VoiceOutputCommand(
                version="RC33-VOICE-OUTPUT-ADAPTER",
                command="SPEAK",
                event_id="rc47-controlled-audio-test",
                text=phrase,
                priority="NORMAL",
                interrupt=False,
                voice_profile=self.config.voice_profile,
                language=self.config.language,
                speech_rate=self.config.speech_rate,
                estimated_duration_seconds=3.0,
                source_version="RC47-CONTROLLED-REAL-AUDIO-TEST",
            )
            tts_result = gateway.speak(command)
            return ControlledAudioTestResult(
                version=self.VERSION,
                attempted=True,
                executed=True,
                backend=capability.configured_backend,
                selected_voice=capability.selected_voice,
                text=phrase,
                accepted=bool(tts_result.accepted),
                completed=bool(tts_result.completed),
                error=str(tts_result.error or "") or None,
            )
        except Exception as exc:
            return ControlledAudioTestResult(
                version=self.VERSION,
                attempted=True,
                executed=True,
                backend=capability.configured_backend,
                selected_voice=capability.selected_voice,
                text=phrase,
                accepted=False,
                completed=False,
                error=str(exc),
            )
