"""
BookDiagnostics RC64 - Voice Status Export Contract.

Empacota o bundle RC62 em um envelope JSON estavel e versionado para logs,
diagnostico e futuras interfaces. Nao inicia audio e nao altera o nucleo.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json


@dataclass(slots=True, frozen=True)
class VoiceStatusExport:
    version: str
    schema: str
    generated_at: str
    status: str
    payload: dict
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True)


class BookDiagnosticsVoiceStatusExporter:
    VERSION = "RC64-VOICE-STATUS-EXPORT-CONTRACT"
    SCHEMA = "copiloto.voice.status.v1"
    SOURCE_VERSION = "RC62-VOICE-STATUS-BUNDLE"

    def export(self, bundle, *, generated_at: datetime | None = None) -> VoiceStatusExport:
        payload = self._payload(bundle)
        self._validate(payload)

        health = dict(payload.get("health_report") or {})
        status = str(health.get("status", "UNKNOWN") or "UNKNOWN").upper().strip()
        instant = generated_at or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        instant = instant.astimezone(timezone.utc)

        return VoiceStatusExport(
            version=self.VERSION,
            schema=self.SCHEMA,
            generated_at=instant.isoformat().replace("+00:00", "Z"),
            status=status,
            payload=dict(payload),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC64 requires RC62 voice status bundle")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC62 voice status bundle")
        health = dict(payload.get("health_report") or {})
        projection = dict(payload.get("dashboard_projection") or {})
        widget = dict(payload.get("dashboard_widget") or {})
        statuses = {str(item.get("status", "")) for item in (health, projection, widget)}
        if len(statuses) != 1 or "" in statuses:
            raise ValueError("RC64 requires consistent RC62 status payloads")
