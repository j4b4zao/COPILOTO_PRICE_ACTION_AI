"""
BookDiagnostics RC55 - Voice Integration Status Snapshot.

Consolida em um unico snapshot readonly o estado do servico de voz, diagnostico,
readiness e disponibilidade do orquestrador, sem iniciar fala e sem conectar ao
loop operacional do bot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceIntegrationStatusSnapshot:
    version: str
    service_enabled: bool
    service_available: bool
    backend: str
    backend_healthy: bool
    diagnostics_ready: bool
    readiness_reason: str
    operational_voice_allowed: bool
    orchestrator_initialized: bool
    queue_size: int
    session_state: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceIntegrationStatus:
    VERSION = "RC55-VOICE-INTEGRATION-STATUS"

    def __init__(self, *, voice_service):
        if voice_service is None:
            raise ValueError("voice_service is required")
        self.voice_service = voice_service

    def snapshot(self) -> VoiceIntegrationStatusSnapshot:
        service = self._payload(self.voice_service.snapshot())
        diagnostics = self._payload(self.voice_service.diagnostics())
        readiness = self._payload(self.voice_service.readiness())

        self._validate_service(service)
        self._validate_diagnostics(diagnostics)
        self._validate_readiness(readiness)

        return VoiceIntegrationStatusSnapshot(
            version=self.VERSION,
            service_enabled=bool(service.get("enabled", False)),
            service_available=bool(service.get("available", False)),
            backend=str(service.get("backend", "DISABLED")),
            backend_healthy=bool(service.get("backend_healthy", False)),
            diagnostics_ready=bool(diagnostics.get("ready_for_real_audio", False)),
            readiness_reason=str(readiness.get("reason", "UNKNOWN")),
            operational_voice_allowed=bool(readiness.get("operational_voice_allowed", False)),
            orchestrator_initialized=getattr(self.voice_service, "_orchestrator", None) is not None,
            queue_size=int(service.get("queue_size", 0)),
            session_state=str(service.get("session_state", "IDLE")),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    @staticmethod
    def _validate_service(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC39-VOICE-SERVICE-INTEGRATION":
            raise PermissionError("RC55 requires RC39 voice service snapshot")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid voice service snapshot")

    @staticmethod
    def _validate_diagnostics(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC45-VOICE-CAPABILITY-DIAGNOSTICS":
            raise PermissionError("RC55 requires RC45 diagnostics")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid diagnostics snapshot")

    @staticmethod
    def _validate_readiness(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC49-VOICE-READINESS-GATE":
            raise PermissionError("RC55 requires RC49 readiness")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid readiness snapshot")
