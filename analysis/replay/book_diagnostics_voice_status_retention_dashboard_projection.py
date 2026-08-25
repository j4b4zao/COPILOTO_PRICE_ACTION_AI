"""
BookDiagnostics RC76 - Voice Status Retention Dashboard Projection.

Projeta exclusivamente o health summary RC73 para consumo visual de dashboard.
Nao acessa filesystem, nao inicia audio e nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionDashboardProjection:
    version: str
    status: str
    label: str
    summary: str
    directory: str
    directory_exists: bool
    prefix: str
    keep: int
    existing_count: int
    retained_count: int
    excess_count: int
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionDashboardProjector:
    VERSION = "RC76-VOICE-STATUS-RETENTION-DASHBOARD-PROJECTION"
    SOURCE_VERSION = "RC73-VOICE-STATUS-RETENTION-HEALTH"

    LABELS = {
        "EMPTY": "Sem snapshots",
        "WITHIN_LIMIT": "Retencao dentro do limite",
        "OVER_LIMIT": "Retencao acima do limite",
    }

    def project(self, retention_health) -> VoiceStatusRetentionDashboardProjection:
        payload = self._payload(retention_health)
        self._validate(payload)

        status = str(payload.get("status", "") or "").upper().strip()
        if status not in self.LABELS:
            raise ValueError("invalid RC73 retention health status")

        return VoiceStatusRetentionDashboardProjection(
            version=self.VERSION,
            status=status,
            label=self.LABELS[status],
            summary=str(payload.get("summary", "") or ""),
            directory=str(payload.get("directory", "") or ""),
            directory_exists=bool(payload.get("directory_exists", False)),
            prefix=str(payload.get("prefix", "") or ""),
            keep=int(payload.get("keep", 0)),
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
            raise PermissionError("RC76 requires RC73 retention health")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC73 retention health")

        keep = int(payload.get("keep", 0))
        existing = int(payload.get("existing_count", -1))
        retained = int(payload.get("retained_count", -1))
        excess = int(payload.get("would_remove_count", -1))
        if keep < 1:
            raise ValueError("RC76 requires keep >= 1")
        if min(existing, retained, excess) < 0:
            raise ValueError("RC76 requires non-negative retention counts")
        if retained + excess != existing:
            raise ValueError("RC76 requires consistent RC73 retention counts")
