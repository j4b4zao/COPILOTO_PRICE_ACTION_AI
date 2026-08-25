"""Sink TTS real e opcional para coaching psicológico (RC18)."""

from __future__ import annotations

from analysis.replay.book_diagnostics_tts_backend import (
    BookDiagnosticsTTSGateway,
)
from analysis.replay.book_diagnostics_voice_output import (
    VoiceOutputCommand,
)
from analysis.replay.book_diagnostics_windows_sapi_backend import (
    WindowsSAPITTSBackend,
)


class PsychologyTTSBackendSink:
    """Adapta coaching ao contrato readonly RC33/RC35 de TTS."""

    NAME = "PsychologyTTSBackendSink"
    VERSION = "RC18"

    def __init__(
        self,
        *,
        backend,
        language="pt-BR",
        voice_profile="BRITISH_CALM_PRECISE_ASSISTANT",
        speech_rate=1.0,
    ):
        for method in ("speak", "stop", "healthcheck"):
            if not callable(getattr(backend, method, None)):
                raise TypeError(
                    f"backend deve expor {method}()."
                )
        language = str(language or "").strip()
        voice_profile = str(voice_profile or "").strip()
        if not language:
            raise ValueError("language não pode ser vazio.")
        if not voice_profile:
            raise ValueError("voice_profile não pode ser vazio.")
        if (
            isinstance(speech_rate, bool)
            or not isinstance(speech_rate, (int, float))
            or not 0.5 <= float(speech_rate) <= 2.0
        ):
            raise ValueError(
                "speech_rate deve ficar entre 0.5 e 2.0."
            )

        self.backend = backend
        self.gateway = BookDiagnosticsTTSGateway(backend=backend)
        self.language = language
        self.voice_profile = voice_profile
        self.speech_rate = float(speech_rate)
        self._sequence = 0
        self.last_command = None
        self.last_result = None

    def speak(self, *, text, priority, code):
        text = " ".join(str(text or "").split())
        code = str(code or "").strip().upper()
        priority = str(priority or "").strip().upper()
        if not text:
            raise ValueError("text não pode ser vazio.")
        if not code:
            raise ValueError("code não pode ser vazio.")
        if priority not in {"NORMAL", "CAUTION", "URGENT"}:
            raise ValueError("priority inválida.")
        if not self.gateway.healthcheck():
            self.last_command = None
            self.last_result = None
            return False

        self._sequence += 1
        command = VoiceOutputCommand(
            version="RC33-VOICE-OUTPUT-ADAPTER",
            command="SPEAK",
            event_id=(
                f"psychology-{self._sequence:08d}-"
                f"{code.casefold()}"
            ),
            text=text,
            priority=priority,
            interrupt=(priority == "URGENT"),
            voice_profile=self.voice_profile,
            language=self.language,
            speech_rate=self.speech_rate,
            estimated_duration_seconds=max(
                1.0,
                len(text) / 14.0,
            ),
            source_version="TRADER-PSYCHOLOGY-RC18",
        )
        self.last_command = command
        result = self.gateway.speak(command)
        self.last_result = result
        return bool(
            result.accepted
            and result.completed
            and not result.error
        )

    def healthcheck(self):
        return self.gateway.healthcheck()

    def stop(self):
        event_id = (
            self.last_command.event_id
            if self.last_command is not None
            else None
        )
        return self.gateway.stop(event_id)


class WindowsSAPIPsychologyVoiceSink(PsychologyTTSBackendSink):
    """Atalho explícito para o backend Windows SAPI já existente."""

    NAME = "WindowsSAPIPsychologyVoiceSink"

    def __init__(
        self,
        *,
        backend=None,
        language="pt-BR",
        voice_profile="BRITISH_CALM_PRECISE_ASSISTANT",
        speech_rate=1.0,
    ):
        super().__init__(
            backend=backend or WindowsSAPITTSBackend(),
            language=language,
            voice_profile=voice_profile,
            speech_rate=speech_rate,
        )
