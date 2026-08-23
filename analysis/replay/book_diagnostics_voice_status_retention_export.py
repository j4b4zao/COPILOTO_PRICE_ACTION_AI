"""
BookDiagnostics RC83 - Voice Status Retention Export Contract.

Empacota o bundle RC80 em um envelope JSON estavel e versionado para logs,
diagnostico e futuras interfaces. Nao acessa filesystem, nao inicia audio e
nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionExport:
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


class BookDiagnosticsVoiceStatusRetentionExporter:
    VERSION = "RC83-VOICE-STATUS-RETENTION-EXPORT-CONTRACT"
    SCHEMA = "copiloto.voice.status.retention.v1"
    SOURCE_VERSION = "RC80-VOICE-STATUS-RETENTION-BUNDLE"

    def export(self, bundle, *, generated_at: datetime | None = None) -> VoiceStatusRetentionExport:
        payload = self._payload(bundle)
        self._validate(payload)

        health = dict(payload.get("health") or {})
        status = str(health.get("status", "UNKNOWN") or "UNKNOWN").upper().strip()

        instant = generated_at or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        instant = instant.astimezone(timezone.utc)

        return VoiceStatusRetentionExport(
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
            raise PermissionError("RC83 requires RC80 retention status bundle")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC80 retention status bundle")

        health = dict(payload.get("health") or {})
        projection = dict(payload.get("dashboard_projection") or {})
        widget = dict(payload.get("dashboard_widget") or {})
        statuses = {str(item.get("status", "")) for item in (health, projection, widget)}
        if len(statuses) != 1 or "" in statuses:
            raise ValueError("RC83 requires consistent RC80 retention status payloads")
        status = next(iter(statuses))
        if status not in {"EMPTY", "WITHIN_LIMIT", "OVER_LIMIT"}:
            raise ValueError("RC83 invalid retention status")
