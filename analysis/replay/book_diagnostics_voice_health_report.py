"""
BookDiagnostics RC56 - Voice Integration Health Report.

Transforma o snapshot RC55 em um estado textual simples para terminal/dashboard,
sem iniciar fala e sem alterar o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceHealthReport:
    version: str
    status: str
    summary: str
    backend: str
    backend_healthy: bool
    operational_voice_allowed: bool
    readiness_reason: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceHealthReporter:
    VERSION = "RC56-VOICE-INTEGRATION-HEALTH-REPORT"
    SOURCE_VERSION = "RC55-VOICE-INTEGRATION-STATUS"

    def build(self, integration_status) -> VoiceHealthReport:
        payload = self._payload(integration_status)
        self._validate(payload)

        enabled = bool(payload.get("service_enabled", False))
        available = bool(payload.get("service_available", False))
        healthy = bool(payload.get("backend_healthy", False))
        diagnostics_ready = bool(payload.get("diagnostics_ready", False))
        operational_allowed = bool(payload.get("operational_voice_allowed", False))
        readiness_reason = str(payload.get("readiness_reason", "UNKNOWN") or "UNKNOWN")
        backend = str(payload.get("backend", "DISABLED") or "DISABLED")

        if not enabled:
            status = "DISABLED"
            summary = "Voice service is disabled."
        elif not available:
            status = "DEGRADED"
            summary = "Voice service is enabled but runtime is unavailable."
        elif not healthy:
            status = "DEGRADED"
            summary = f"Voice backend {backend} is not healthy."
        elif not diagnostics_ready:
            status = "DIAGNOSTICS_PENDING"
            summary = "Voice diagnostics are not ready for real audio."
        elif not operational_allowed:
            status = "TEST_REQUIRED" if readiness_reason == "CONTROLLED_TEST_REQUIRED" else "DEGRADED"
            summary = "Controlled audio validation is required." if status == "TEST_REQUIRED" else f"Operational voice blocked: {readiness_reason}."
        else:
            status = "READY"
            summary = f"Voice integration is ready with backend {backend}."

        return VoiceHealthReport(
            version=self.VERSION,
            status=status,
            summary=summary,
            backend=backend,
            backend_healthy=healthy,
            operational_voice_allowed=operational_allowed,
            readiness_reason=readiness_reason,
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC56 requires RC55 integration status")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC55 integration status")
