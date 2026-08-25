"""
BookDiagnostics RC33 - Voice Output Adapter.

Ponte segura entre a fila RC32 e uma futura implementacao TTS.
O adapter produz comandos estruturados de saida, mas nao sintetiza audio,
nao executa IO externo e nao altera Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class VoiceOutputCommand:
    version: str
    command: str
    event_id: str
    text: str
    priority: str
    interrupt: bool
    voice_profile: str
    language: str
    speech_rate: float
    estimated_duration_seconds: float
    source_version: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class VoiceOutputSink(Protocol):
    """Contrato minimo para um backend futuro de voz."""

    def submit(self, command: VoiceOutputCommand) -> None:
        ...


class NullVoiceOutputSink:
    """Sink seguro padrao: aceita o comando sem produzir audio."""

    def submit(self, command: VoiceOutputCommand) -> None:
        return None


class BookDiagnosticsVoiceOutputAdapter:
    VERSION = "RC33-VOICE-OUTPUT-ADAPTER"
    SOURCE_VERSION = "RC31-VOICE-EVENT-CONTRACT"

    def __init__(self, *, sink: VoiceOutputSink | None = None):
        self.sink = sink or NullVoiceOutputSink()

    def prepare(self, voice_event) -> VoiceOutputCommand:
        payload = self._payload(voice_event)
        self._validate(payload)

        priority = str(payload["priority"]).upper()
        interrupt = bool(payload.get("interrupt_allowed", False)) and priority == "URGENT"

        return VoiceOutputCommand(
            version=self.VERSION,
            command="SPEAK",
            event_id=str(payload["event_id"]),
            text=str(payload["text"]).strip(),
            priority=priority,
            interrupt=interrupt,
            voice_profile=str(payload["voice_profile"]),
            language=str(payload["language"]),
            speech_rate=float(payload["speech_rate"]),
            estimated_duration_seconds=float(payload["estimated_duration_seconds"]),
            source_version=self.SOURCE_VERSION,
        )

    def dispatch(self, voice_event) -> VoiceOutputCommand:
        command = self.prepare(voice_event)
        self.sink.submit(command)
        return command

    def dispatch_next(self, queue) -> VoiceOutputCommand | None:
        """Retira somente o proximo evento priorizado pela RC32."""
        event = queue.pop_next()
        if event is None:
            return None
        return self.dispatch(event)

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC33 requires RC31 voice event")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC33 requires readonly voice event")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC33 rejects decision-affecting event")

        required = (
            "event_id",
            "text",
            "priority",
            "voice_profile",
            "language",
            "speech_rate",
            "estimated_duration_seconds",
        )
        for field in required:
            if field not in payload:
                raise ValueError(f"missing voice field: {field}")

        if not str(payload["event_id"]).strip():
            raise ValueError("event_id cannot be empty")
        if not str(payload["text"]).strip():
            raise ValueError("voice text cannot be empty")

        priority = str(payload["priority"]).upper()
        if priority not in {"NORMAL", "CAUTION", "URGENT"}:
            raise ValueError("invalid voice priority")

        speech_rate = float(payload["speech_rate"])
        if speech_rate <= 0:
            raise ValueError("speech_rate must be positive")

        duration = float(payload["estimated_duration_seconds"])
        if duration <= 0:
            raise ValueError("estimated duration must be positive")
