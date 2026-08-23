"""
BookDiagnostics RC85 - Voice Status Retention File Export.

Persiste explicitamente o envelope RC83 em arquivo JSON com escrita atomica.
Nao inicia audio, nao altera Decision e nao e conectado ao loop principal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import tempfile


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionFileExportResult:
    version: str
    path: str
    bytes_written: int
    status: str
    schema: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionFileExporter:
    VERSION = "RC85-VOICE-STATUS-RETENTION-FILE-EXPORT"
    SOURCE_VERSION = "RC83-VOICE-STATUS-RETENTION-EXPORT-CONTRACT"
    SCHEMA = "copiloto.voice.status.retention.v1"

    def write(self, status_export, destination) -> VoiceStatusRetentionFileExportResult:
        payload = self._payload(status_export)
        self._validate(payload)

        target = Path(destination).expanduser()
        if not target.name:
            raise ValueError("destination must include a file name")
        if target.suffix.lower() != ".json":
            raise ValueError("RC85 destination must use .json extension")

        target = target.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(status_export, "to_json"):
            text = status_export.to_json(indent=2)
        else:
            import json
            text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        if not text.endswith("\n"):
            text += "\n"
        encoded = text.encode("utf-8")

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(target.parent),
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

        return VoiceStatusRetentionFileExportResult(
            version=self.VERSION,
            path=str(target),
            bytes_written=len(encoded),
            status=str(payload.get("status", "UNKNOWN") or "UNKNOWN"),
            schema=str(payload.get("schema", "") or ""),
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC85 requires RC83 retention status export")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC83 retention status export")
        if str(payload.get("schema", "")) != self.SCHEMA:
            raise ValueError("unsupported retention status schema")
        status = str(payload.get("status", "") or "").strip()
        if status not in {"EMPTY", "WITHIN_LIMIT", "OVER_LIMIT"}:
            raise ValueError("invalid retention status")
