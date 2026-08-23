"""
BookDiagnostics RC87 - Voice Retention Status Export Rotation.

Gera historico rotacionado do proprio status de retencao, separado dos snapshots
normais de voz. Usa apenas o exportador RC85, remove somente arquivos com prefixo
explicito desta serie e nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import re


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionExportRotationResult:
    version: str
    source_directory: str
    export_directory: str
    source_prefix: str
    export_prefix: str
    source_keep: int
    export_keep: int
    current_file: str
    retained_files: tuple[str, ...]
    removed_files: tuple[str, ...]
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionExportRotationManager:
    VERSION = "RC87-VOICE-STATUS-RETENTION-EXPORT-ROTATION"

    def export_and_rotate(
        self,
        *,
        voice_service,
        source_directory,
        export_directory,
        source_keep: int = 20,
        source_prefix: str = "voice_status",
        export_keep: int = 20,
        export_prefix: str = "voice_retention_status",
        generated_at: datetime | None = None,
    ) -> VoiceStatusRetentionExportRotationResult:
        if int(source_keep) < 1:
            raise ValueError("RC87 source_keep must be >= 1")
        if int(export_keep) < 1:
            raise ValueError("RC87 export_keep must be >= 1")

        safe_source_prefix = self._validate_prefix(source_prefix, "source_prefix")
        safe_export_prefix = self._validate_prefix(export_prefix, "export_prefix")
        if safe_source_prefix == safe_export_prefix:
            raise ValueError("RC87 source_prefix and export_prefix must differ")

        source_folder = Path(source_directory).expanduser().resolve()
        export_folder = Path(export_directory).expanduser().resolve()
        export_folder.mkdir(parents=True, exist_ok=True)

        instant = generated_at or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        instant = instant.astimezone(timezone.utc)
        stamp = instant.strftime("%Y%m%dT%H%M%S%fZ")
        target = export_folder / f"{safe_export_prefix}_{stamp}.json"

        write_result = voice_service.export_retention_status_file(
            source_folder,
            target,
            keep=int(source_keep),
            prefix=safe_source_prefix,
            generated_at=instant,
        )
        current = Path(write_result.path).resolve()

        candidates = sorted(
            (
                path.resolve()
                for path in export_folder.glob(f"{safe_export_prefix}_*.json")
                if path.is_file()
            ),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        retained = candidates[: int(export_keep)]
        removed = candidates[int(export_keep) :]
        for path in removed:
            path.unlink(missing_ok=True)

        return VoiceStatusRetentionExportRotationResult(
            version=self.VERSION,
            source_directory=str(source_folder),
            export_directory=str(export_folder),
            source_prefix=safe_source_prefix,
            export_prefix=safe_export_prefix,
            source_keep=int(source_keep),
            export_keep=int(export_keep),
            current_file=str(current),
            retained_files=tuple(str(path) for path in retained),
            removed_files=tuple(str(path) for path in removed),
        )

    @staticmethod
    def _validate_prefix(prefix: str, label: str) -> str:
        value = str(prefix or "").strip()
        if not value:
            raise ValueError(f"RC87 {label} cannot be empty")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(f"RC87 {label} may contain only letters, numbers, _ and -")
        return value
