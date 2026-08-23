"""
BookDiagnostics RC98 - Voice Retention Export Rotation Dashboard Widget Contract.

Transforma a projecao RC96 da segunda serie historica em um contrato visual
minimo e readonly para futuro consumo por dashboard. Nao renderiza UI, nao
acessa filesystem, nao inicia audio e nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionExportRotationDashboardWidget:
    version: str
    title: str
    status: str
    label: str
    detail: str
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


class BookDiagnosticsVoiceStatusRetentionExportRotationDashboardWidgetBuilder:
    VERSION = "RC98-VOICE-STATUS-RETENTION-EXPORT-ROTATION-DASHBOARD-WIDGET-CONTRACT"
    SOURCE_VERSION = "RC96-VOICE-STATUS-RETENTION-EXPORT-ROTATION-DASHBOARD-PROJECTION"
    TITLE = "Voice Retention Export History"

    def build(self, dashboard_projection) -> VoiceStatusRetentionExportRotationDashboardWidget:
        payload = self._payload(dashboard_projection)
        self._validate(payload)

        return VoiceStatusRetentionExportRotationDashboardWidget(
            version=self.VERSION,
            title=self.TITLE,
            status=str(payload.get("status", "") or ""),
            label=str(payload.get("label", "") or ""),
            detail=str(payload.get("summary", "") or ""),
            export_directory=str(payload.get("export_directory", "") or ""),
            directory_exists=bool(payload.get("directory_exists", False)),
            export_prefix=str(payload.get("export_prefix", "") or ""),
            export_keep=int(payload.get("export_keep", 0)),
            existing_count=int(payload.get("existing_count", 0)),
            retained_count=int(payload.get("retained_count", 0)),
            excess_count=int(payload.get("excess_count", 0)),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC98 requires RC96 retention export dashboard projection")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC96 retention export dashboard projection")

        status = str(payload.get("status", "") or "").upper().strip()
        if status not in {"EMPTY", "WITHIN_LIMIT", "OVER_LIMIT"}:
            raise ValueError("invalid RC96 retention export dashboard status")
        if not str(payload.get("label", "") or "").strip():
            raise ValueError("RC96 retention export dashboard label cannot be empty")

        export_keep = int(payload.get("export_keep", 0))
        existing = int(payload.get("existing_count", -1))
        retained = int(payload.get("retained_count", -1))
        excess = int(payload.get("excess_count", -1))
        if export_keep < 1:
            raise ValueError("RC98 requires export_keep >= 1")
        if min(existing, retained, excess) < 0:
            raise ValueError("RC98 requires non-negative retention export counts")
        if retained + excess != existing:
            raise ValueError("RC98 requires consistent RC96 retention export counts")
