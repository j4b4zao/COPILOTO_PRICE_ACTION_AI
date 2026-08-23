"""
BookDiagnostics RC58 - Voice Health Dashboard Projection.

Projeta exclusivamente o health report RC56 para consumo visual de dashboard.
Nao duplica regras de saude, nao inicia audio e nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceHealthDashboardProjection:
    version: str
    status: str
    label: str
    summary: str
    backend: str
    backend_healthy: bool
    operational_voice_allowed: bool
    readiness_reason: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceHealthDashboardProjector:
    VERSION = "RC58-VOICE-HEALTH-DASHBOARD-PROJECTION"
    SOURCE_VERSION = "RC56-VOICE-INTEGRATION-HEALTH-REPORT"

    LABELS = {
        "DISABLED": "Voz desativada",
        "DIAGNOSTICS_PENDING": "Diagnostico pendente",
        "TEST_REQUIRED": "Teste de audio necessario",
        "READY": "Voz pronta",
        "DEGRADED": "Voz degradada",
    }

    def project(self, health_report) -> VoiceHealthDashboardProjection:
        payload = self._payload(health_report)
        self._validate(payload)
        status = str(payload.get("status", "DEGRADED")).upper().strip()
        if status not in self.LABELS:
            raise ValueError("invalid RC56 health status")

        return VoiceHealthDashboardProjection(
            version=self.VERSION,
            status=status,
            label=self.LABELS[status],
            summary=str(payload.get("summary", "") or ""),
            backend=str(payload.get("backend", "DISABLED") or "DISABLED"),
            backend_healthy=bool(payload.get("backend_healthy", False)),
            operational_voice_allowed=bool(payload.get("operational_voice_allowed", False)),
            readiness_reason=str(payload.get("readiness_reason", "UNKNOWN") or "UNKNOWN"),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC58 requires RC56 health report")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC56 health report")
