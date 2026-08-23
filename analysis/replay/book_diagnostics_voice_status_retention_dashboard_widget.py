"""
BookDiagnostics RC78 - Voice Status Retention Dashboard Widget Contract.

Transforma a projecao RC76 em um contrato visual minimo e readonly para futuro
consumo por qualquer dashboard. Nao renderiza UI, nao acessa filesystem, nao
inicia audio e nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionDashboardWidget:
    version: str
    title: str
    status: str
    label: str
    detail: str
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


class BookDiagnosticsVoiceStatusRetentionDashboardWidgetBuilder:
    VERSION = "RC78-VOICE-STATUS-RETENTION-DASHBOARD-WIDGET-CONTRACT"
    SOURCE_VERSION = "RC76-VOICE-STATUS-RETENTION-DASHBOARD-PROJECTION"
    TITLE = "Voice Status Retention"

    def build(self, dashboard_projection) -> VoiceStatusRetentionDashboardWidget:
        payload = self._payload(dashboard_projection)
        self._validate(payload)

        return VoiceStatusRetentionDashboardWidget(
            version=self.VERSION,
            title=self.TITLE,
            status=str(payload.get("status", "") or ""),
            label=str(payload.get("label", "") or ""),
            detail=str(payload.get("summary", "") or ""),
            directory=str(payload.get("directory", "") or ""),
            directory_exists=bool(payload.get("directory_exists", False)),
            prefix=str(payload.get("prefix", "") or ""),
            keep=int(payload.get("keep", 0)),
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
            raise PermissionError("RC78 requires RC76 retention dashboard projection")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC76 retention dashboard projection")

        status = str(payload.get("status", "") or "").upper().strip()
        if status not in {"EMPTY", "WITHIN_LIMIT", "OVER_LIMIT"}:
            raise ValueError("invalid RC76 retention dashboard status")
        if not str(payload.get("label", "") or "").strip():
            raise ValueError("RC76 retention dashboard label cannot be empty")

        keep = int(payload.get("keep", 0))
        existing = int(payload.get("existing_count", -1))
        retained = int(payload.get("retained_count", -1))
        excess = int(payload.get("excess_count", -1))
        if keep < 1:
            raise ValueError("RC78 requires keep >= 1")
        if min(existing, retained, excess) < 0:
            raise ValueError("RC78 requires non-negative retention counts")
        if retained + excess != existing:
            raise ValueError("RC78 requires consistent RC76 retention counts")
