"""
BookDiagnostics RC96 - Voice Retention Export Rotation Dashboard Projection.

Projeta exclusivamente o health summary RC93 da segunda serie historica para
consumo visual futuro de dashboard. Nao acessa filesystem, nao inicia audio e
nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionExportRotationDashboardProjection:
    version: str
    status: str
    label: str
    summary: str
    export_directory: str
    directory_exists: bool
    export_prefix: str
    export_keep: int
    existing_count: int
    retained_count: int
    excess_count: int
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionExportRotationDashboardProjector:
    VERSION = "RC96-VOICE-STATUS-RETENTION-EXPORT-ROTATION-DASHBOARD-PROJECTION"
    SOURCE_VERSION = "RC93-VOICE-STATUS-RETENTION-EXPORT-ROTATION-HEALTH"

    LABELS = {
        "EMPTY": "Sem historico de retencao",
        "WITHIN_LIMIT": "Historico de retencao dentro do limite",
        "OVER_LIMIT": "Historico de retencao acima do limite",
    }

    def project(self, health) -> VoiceStatusRetentionExportRotationDashboardProjection:
        payload = self._payload(health)
        self._validate(payload)

        status = str(payload.get("status", "") or "").upper().strip()
        if status not in self.LABELS:
            raise ValueError("invalid RC93 retention export rotation health status")

        return VoiceStatusRetentionExportRotationDashboardProjection(
            version=self.VERSION,
            status=status,
            label=self.LABELS[status],
            summary=str(payload.get("summary", "") or ""),
            export_directory=str(payload.get("export_directory", "") or ""),
            directory_exists=bool(payload.get("directory_exists", False)),
            export_prefix=str(payload.get("export_prefix", "") or ""),
            export_keep=int(payload.get("export_keep", 0)),
            existing_count=int(payload.get("existing_count", 0)),
            retained_count=int(payload.get("retained_count", 0)),
            excess_count=int(payload.get("would_remove_count", 0)),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC96 requires RC93 retention export rotation health")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC93 retention export rotation health")

        export_keep = int(payload.get("export_keep", 0))
        existing = int(payload.get("existing_count", -1))
        retained = int(payload.get("retained_count", -1))
        excess = int(payload.get("would_remove_count", -1))
        if export_keep < 1:
            raise ValueError("RC96 requires export_keep >= 1")
        if min(existing, retained, excess) < 0:
            raise ValueError("RC96 requires non-negative retention export counts")
        if retained + excess != existing:
            raise ValueError("RC96 requires consistent RC93 retention export counts")
