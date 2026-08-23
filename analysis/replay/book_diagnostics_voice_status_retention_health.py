"""
BookDiagnostics RC73 - Voice Status Retention Health Summary.

Resume a inspecao RC70 em um estado simples e readonly para terminal/dashboard.
Nao acessa filesystem diretamente, nao inicia audio e nao altera Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionHealth:
    version: str
    status: str
    summary: str
    directory: str
    directory_exists: bool
    prefix: str
    keep: int
    existing_count: int
    retained_count: int
    would_remove_count: int
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionHealthReporter:
    VERSION = "RC73-VOICE-STATUS-RETENTION-HEALTH"
    SOURCE_VERSION = "RC70-VOICE-STATUS-RETENTION-INSPECTION"

    def build(self, inspection) -> VoiceStatusRetentionHealth:
        payload = self._payload(inspection)
        self._validate(payload)

        existing_count = len(tuple(payload.get("existing_files") or ()))
        retained_count = len(tuple(payload.get("retained_files") or ()))
        would_remove_count = len(tuple(payload.get("would_remove_files") or ()))
        directory_exists = bool(payload.get("directory_exists", False))

        if existing_count == 0:
            status = "EMPTY"
            summary = "No voice status snapshots are present."
        elif would_remove_count > 0:
            status = "OVER_LIMIT"
            summary = f"Retention exceeds the configured limit by {would_remove_count} snapshot(s)."
        else:
            status = "WITHIN_LIMIT"
            summary = f"Retention is within the configured limit with {existing_count} snapshot(s)."

        return VoiceStatusRetentionHealth(
            version=self.VERSION,
            status=status,
            summary=summary,
            directory=str(payload.get("directory", "")),
            directory_exists=directory_exists,
            prefix=str(payload.get("prefix", "")),
            keep=int(payload.get("keep", 0)),
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
            raise PermissionError("RC73 requires RC70 retention inspection")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid RC70 retention inspection")
        if int(payload.get("keep", 0)) < 1:
            raise ValueError("RC73 requires keep >= 1")

        existing = tuple(payload.get("existing_files") or ())
        retained = tuple(payload.get("retained_files") or ())
        would_remove = tuple(payload.get("would_remove_files") or ())
        if len(retained) + len(would_remove) != len(existing):
            raise ValueError("RC73 requires consistent RC70 retention counts")
