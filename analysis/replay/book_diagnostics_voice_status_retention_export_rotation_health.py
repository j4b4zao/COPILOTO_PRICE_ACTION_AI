"""
BookDiagnostics RC93 - Voice Retention Export Rotation Health Summary.

Resume a inspecao readonly RC90 da segunda serie historica em um estado simples
para terminal/dashboard. Nao acessa filesystem diretamente, nao inicia audio e
nao altera Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionExportRotationHealth:
    version: str
    status: str
    summary: str
    export_directory: str
    directory_exists: bool
    export_prefix: str
    export_keep: int
    existing_count: int
    retained_count: int
    would_remove_count: int
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionExportRotationHealthReporter:
    VERSION = "RC93-VOICE-STATUS-RETENTION-EXPORT-ROTATION-HEALTH"
    SOURCE_VERSION = "RC90-VOICE-STATUS-RETENTION-EXPORT-ROTATION-INSPECTION"

    def build(self, inspection) -> VoiceStatusRetentionExportRotationHealth:
        payload = self._payload(inspection)
        self._validate(payload)

        existing_count = len(tuple(payload.get("existing_files") or ()))
        retained_count = len(tuple(payload.get("retained_files") or ()))
        would_remove_count = len(tuple(payload.get("would_remove_files") or ()))
        directory_exists = bool(payload.get("directory_exists", False))

        if existing_count == 0:
            status = "EMPTY"
            summary = "No retention status export snapshots are present."
        elif would_remove_count > 0:
            status = "OVER_LIMIT"
            summary = f"Retention export history exceeds the configured limit by {would_remove_count} snapshot(s)."
        else:
            status = "WITHIN_LIMIT"
            summary = f"Retention export history is within the configured limit with {existing_count} snapshot(s)."

        return VoiceStatusRetentionExportRotationHealth(
            version=self.VERSION,
            status=status,
            summary=summary,
            export_directory=str(payload.get("export_directory", "")),
            directory_exists=directory_exists,
            export_prefix=str(payload.get("export_prefix", "")),
            export_keep=int(payload.get("export_keep", 0)),
            existing_count=existing_count,
            retained_count=retained_count,
            would_remove_count=would_remove_count,
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict) -> None:
        if str(payload.get("version", "")) != self.SOURCE_VERSION:
            raise PermissionError("RC93 requires RC90 retention export rotation inspection")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC90 retention export rotation inspection")
        if int(payload.get("export_keep", 0)) < 1:
            raise ValueError("RC93 requires export_keep >= 1")

        existing = tuple(payload.get("existing_files") or ())
        retained = tuple(payload.get("retained_files") or ())
        would_remove = tuple(payload.get("would_remove_files") or ())
        if len(retained) + len(would_remove) != len(existing):
            raise ValueError("RC93 requires consistent RC90 retention export counts")
