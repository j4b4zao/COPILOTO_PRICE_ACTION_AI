"""
BookDiagnostics RC60 - Dashboard Voice Widget Contract.

Transforma a projecao RC58 em um contrato visual minimo e readonly para futuro
consumo por qualquer dashboard. Nao renderiza UI, nao inicia audio e nao altera
o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceDashboardWidget:
    version: str
    title: str
    status: str
    label: str
    detail: str
    backend: str
    backend_healthy: bool
    operational_voice_allowed: bool
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceDashboardWidgetBuilder:
    VERSION = "RC60-DASHBOARD-VOICE-WIDGET-CONTRACT"
    SOURCE_VERSION = "RC58-VOICE-HEALTH-DASHBOARD-PROJECTION"
    TITLE = "Voice Assistant"

    def build(self, dashboard_projection) -> VoiceDashboardWidget:
        payload = self._payload(dashboard_projection)
        self._validate(payload)

        return VoiceDashboardWidget(
            version=self.VERSION,
            title=self.TITLE,
            status=str(payload.get("status", "DEGRADED") or "DEGRADED"),
            label=str(payload.get("label", "") or ""),
            detail=str(payload.get("summary", "") or ""),
            backend=str(payload.get("backend", "DISABLED") or "DISABLED"),
            backend_healthy=bool(payload.get("backend_healthy", False)),
            operational_voice_allowed=bool(payload.get("operational_voice_allowed", False)),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC60 requires RC58 dashboard projection")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC58 dashboard projection")
        if not str(payload.get("label", "") or "").strip():
            raise ValueError("RC58 dashboard label cannot be empty")
