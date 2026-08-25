"""
BookDiagnostics RC80 - Voice Status Retention Bundle.

Agrupa inspection RC70, health RC73, dashboard projection RC76 e dashboard
widget RC78 em um unico payload readonly para consumo por interfaces futuras.
Nao acessa filesystem diretamente, nao inicia audio e nao altera Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionBundle:
    version: str
    inspection: dict
    health: dict
    dashboard_projection: dict
    dashboard_widget: dict
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionBundleBuilder:
    VERSION = "RC80-VOICE-STATUS-RETENTION-BUNDLE"
    INSPECTION_VERSION = "RC70-VOICE-STATUS-RETENTION-INSPECTION"
    HEALTH_VERSION = "RC73-VOICE-STATUS-RETENTION-HEALTH"
    PROJECTION_VERSION = "RC76-VOICE-STATUS-RETENTION-DASHBOARD-PROJECTION"
    WIDGET_VERSION = "RC78-VOICE-STATUS-RETENTION-DASHBOARD-WIDGET-CONTRACT"

    def build(self, *, inspection, health, dashboard_projection, dashboard_widget) -> VoiceStatusRetentionBundle:
        inspection_payload = self._payload(inspection)
        health_payload = self._payload(health)
        projection_payload = self._payload(dashboard_projection)
        widget_payload = self._payload(dashboard_widget)

        self._validate(inspection_payload, self.INSPECTION_VERSION, "inspection")
        self._validate(health_payload, self.HEALTH_VERSION, "health")
        self._validate(projection_payload, self.PROJECTION_VERSION, "dashboard projection")
        self._validate(widget_payload, self.WIDGET_VERSION, "dashboard widget")

        self._validate_status(health_payload, projection_payload, widget_payload)
        self._validate_context(inspection_payload, health_payload, projection_payload, widget_payload)
        self._validate_counts(inspection_payload, health_payload, projection_payload, widget_payload)

        return VoiceStatusRetentionBundle(
            version=self.VERSION,
            inspection=dict(inspection_payload),
            health=dict(health_payload),
            dashboard_projection=dict(projection_payload),
            dashboard_widget=dict(widget_payload),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    @staticmethod
    def _validate(payload: dict, expected_version: str, label: str) -> None:
        if str(payload.get("version", "")) != expected_version:
            raise PermissionError(f"RC80 requires valid {label}")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError(f"invalid {label}")

    @staticmethod
    def _validate_status(health: dict, projection: dict, widget: dict) -> None:
        status = str(health.get("status", ""))
        if status not in {"EMPTY", "WITHIN_LIMIT", "OVER_LIMIT"}:
            raise ValueError("RC80 invalid retention status")
        if status != str(projection.get("status", "")) or status != str(widget.get("status", "")):
            raise ValueError("RC80 retention status mismatch")

    @staticmethod
    def _validate_context(inspection: dict, health: dict, projection: dict, widget: dict) -> None:
        for key in ("directory", "prefix", "keep"):
            expected = inspection.get(key)
            if health.get(key) != expected or projection.get(key) != expected or widget.get(key) != expected:
                raise ValueError(f"RC80 retention {key} mismatch")

    @staticmethod
    def _validate_counts(inspection: dict, health: dict, projection: dict, widget: dict) -> None:
        existing = len(tuple(inspection.get("existing_files") or ()))
        retained = len(tuple(inspection.get("retained_files") or ()))
        excess = len(tuple(inspection.get("would_remove_files") or ()))
        if retained + excess != existing:
            raise ValueError("RC80 inconsistent RC70 retention counts")

        expected = (existing, retained, excess)
        health_counts = (
            int(health.get("existing_count", -1)),
            int(health.get("retained_count", -1)),
            int(health.get("would_remove_count", -1)),
        )
        projection_counts = (
            int(projection.get("existing_count", -1)),
            int(projection.get("retained_count", -1)),
            int(projection.get("excess_count", -1)),
        )
        widget_counts = (
            int(widget.get("existing_count", -1)),
            int(widget.get("retained_count", -1)),
            int(widget.get("excess_count", -1)),
        )
        if health_counts != expected or projection_counts != expected or widget_counts != expected:
            raise ValueError("RC80 retention count mismatch")
