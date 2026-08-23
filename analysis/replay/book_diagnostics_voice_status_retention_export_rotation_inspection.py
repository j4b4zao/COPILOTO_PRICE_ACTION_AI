"""
BookDiagnostics RC90 - Voice Retention Status Export Rotation Inspection.

Inspeciona a politica RC87 sem criar, alterar, exportar ou remover arquivos.
Nao inicia audio e nao altera Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from analysis.replay.book_diagnostics_voice_status_retention_export_rotation import (
    BookDiagnosticsVoiceStatusRetentionExportRotationManager,
)


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionExportRotationInspection:
    version: str
    export_directory: str
    export_prefix: str
    export_keep: int
    directory_exists: bool
    existing_files: tuple[str, ...]
    retained_files: tuple[str, ...]
    would_remove_files: tuple[str, ...]
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionExportRotationInspector:
    VERSION = "RC90-VOICE-STATUS-RETENTION-EXPORT-ROTATION-INSPECTION"

    def inspect(
        self,
        export_directory,
        *,
        export_keep: int = 20,
        export_prefix: str = "voice_retention_status",
    ) -> VoiceStatusRetentionExportRotationInspection:
        if int(export_keep) < 1:
            raise ValueError("RC90 export_keep must be >= 1")

        safe_prefix = BookDiagnosticsVoiceStatusRetentionExportRotationManager._validate_prefix(
            export_prefix,
            "export_prefix",
        )
        folder = Path(export_directory).expanduser().resolve()
        exists = folder.is_dir()

        candidates: list[Path] = []
        if exists:
            candidates = sorted(
                (
                    path.resolve()
                    for path in folder.glob(f"{safe_prefix}_*.json")
                    if path.is_file()
                ),
                key=lambda path: (path.stat().st_mtime_ns, path.name),
                reverse=True,
            )

        retained = candidates[: int(export_keep)]
        would_remove = candidates[int(export_keep) :]

        return VoiceStatusRetentionExportRotationInspection(
            version=self.VERSION,
            export_directory=str(folder),
            export_prefix=safe_prefix,
            export_keep=int(export_keep),
            directory_exists=exists,
            existing_files=tuple(str(path) for path in candidates),
            retained_files=tuple(str(path) for path in retained),
            would_remove_files=tuple(str(path) for path in would_remove),
        )
