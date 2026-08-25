"""
BookDiagnostics RC62 - Voice Status Bundle.

Agrupa health report RC56, dashboard projection RC58 e dashboard widget RC60
em um unico payload readonly para consumo por interfaces futuras.
Nao inicia audio e nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusBundle:
    version: str
    health_report: dict
    dashboard_projection: dict
    dashboard_widget: dict
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusBundleBuilder:
    VERSION = "RC62-VOICE-STATUS-BUNDLE"
    HEALTH_VERSION = "RC56-VOICE-INTEGRATION-HEALTH-REPORT"
    PROJECTION_VERSION = "RC58-VOICE-HEALTH-DASHBOARD-PROJECTION"
    WIDGET_VERSION = "RC60-DASHBOARD-VOICE-WIDGET-CONTRACT"

    def build(self, *, health_report, dashboard_projection, dashboard_widget) -> VoiceStatusBundle:
        health = self._payload(health_report)
        projection = self._payload(dashboard_projection)
        widget = self._payload(dashboard_widget)

        self._validate(health, self.HEALTH_VERSION, "health report")
        self._validate(projection, self.PROJECTION_VERSION, "dashboard projection")
        self._validate(widget, self.WIDGET_VERSION, "dashboard widget")

        if str(health.get("status", "")) != str(projection.get("status", "")):
            raise ValueError("RC62 status mismatch between health and projection")
        if str(projection.get("status", "")) != str(widget.get("status", "")):
            raise ValueError("RC62 status mismatch between projection and widget")

        return VoiceStatusBundle(
            version=self.VERSION,
            health_report=dict(health),
            dashboard_projection=dict(projection),
            dashboard_widget=dict(widget),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    @staticmethod
    def _validate(payload: dict, expected_version: str, label: str) -> None:
        if str(payload.get("version", "")) != expected_version:
            raise PermissionError(f"RC62 requires valid {label}")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError(f"invalid {label}")
