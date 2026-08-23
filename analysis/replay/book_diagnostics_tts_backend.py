"""
BookDiagnostics RC35 - TTS Backend Contract.

Define um contrato generico para futuras implementacoes de Text-to-Speech.
A camada recebe comandos RC33, oferece um backend nulo seguro e descreve
resultados de execucao sem acoplar fornecedor, sintetizar audio por conta
propria ou alterar Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class TTSResult:
    version: str
    backend: str
    event_id: str
    accepted: bool
    completed: bool
    interrupted: bool
    error: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class TTSBackend(Protocol):
    """Contrato minimo para qualquer backend TTS futuro."""

    name: str

    def speak(self, command) -> TTSResult:
        ...

    def stop(self, event_id: str | None = None) -> bool:
        ...

    def healthcheck(self) -> bool:
        ...


class NullTTSBackend:
    """Backend seguro padrao: aceita o contrato sem produzir audio real."""

    name = "NULL_TTS"
    VERSION = "RC35-TTS-BACKEND-CONTRACT"
    SOURCE_VERSION = "RC33-VOICE-OUTPUT-ADAPTER"

    def speak(self, command) -> TTSResult:
        payload = _payload(command)
        _validate_command(payload)
        return TTSResult(
            version=self.VERSION,
            backend=self.name,
            event_id=str(payload["event_id"]),
            accepted=True,
            completed=True,
            interrupted=False,
            error="",
        )

    def stop(self, event_id: str | None = None) -> bool:
        return False

    def healthcheck(self) -> bool:
        return True


class BookDiagnosticsTTSGateway:
    """Gateway neutro entre RC33/RC34 e um backend TTS injetado."""

    VERSION = "RC35-TTS-BACKEND-CONTRACT"

    def __init__(self, *, backend: TTSBackend | None = None):
        self.backend = backend or NullTTSBackend()

    def speak(self, command) -> TTSResult:
        payload = _payload(command)
        _validate_command(payload)
        result = self.backend.speak(command)
        return self._validate_result(result, payload)

    def stop(self, event_id: str | None = None) -> bool:
        if event_id is not None and not str(event_id).strip():
            raise ValueError("event_id cannot be empty")
        return bool(self.backend.stop(event_id))

    def healthcheck(self) -> bool:
        return bool(self.backend.healthcheck())

    def backend_name(self) -> str:
        name = str(getattr(self.backend, "name", "") or "").strip()
        if not name:
            raise ValueError("TTS backend must expose a non-empty name")
        return name

    def _validate_result(self, result, command_payload: dict) -> TTSResult:
        payload = _payload(result)

        if str(payload.get("version", "")) != self.VERSION:
            raise PermissionError("RC35 requires RC35 TTS result")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC35 requires readonly TTS result")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC35 rejects decision-affecting TTS result")
        if str(payload.get("event_id", "")) != str(command_payload["event_id"]):
            raise ValueError("TTS result event_id mismatch")
        if not str(payload.get("backend", "")).strip():
            raise ValueError("TTS result backend cannot be empty")

        return TTSResult(
            version=self.VERSION,
            backend=str(payload["backend"]),
            event_id=str(payload["event_id"]),
            accepted=bool(payload.get("accepted", False)),
            completed=bool(payload.get("completed", False)),
            interrupted=bool(payload.get("interrupted", False)),
            error=str(payload.get("error", "") or ""),
        )


def _payload(value) -> dict:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(value or {})


def _validate_command(payload: dict) -> None:
    if str(payload.get("version", "")) != "RC33-VOICE-OUTPUT-ADAPTER":
        raise PermissionError("RC35 requires RC33 voice output command")
    if str(payload.get("command", "")).upper() != "SPEAK":
        raise PermissionError("RC35 only accepts SPEAK commands")
    if not bool(payload.get("readonly", False)):
        raise PermissionError("RC35 requires readonly command")
    if bool(payload.get("affects_decision", True)):
        raise PermissionError("RC35 rejects decision-affecting command")
    if not str(payload.get("event_id", "")).strip():
        raise ValueError("event_id cannot be empty")
    if not str(payload.get("text", "")).strip():
        raise ValueError("voice text cannot be empty")
    if str(payload.get("priority", "")).upper() not in {"NORMAL", "CAUTION", "URGENT"}:
        raise ValueError("invalid voice priority")
    if float(payload.get("speech_rate", 0)) <= 0:
        raise ValueError("speech_rate must be positive")
    if float(payload.get("estimated_duration_seconds", 0)) <= 0:
        raise ValueError("estimated duration must be positive")
