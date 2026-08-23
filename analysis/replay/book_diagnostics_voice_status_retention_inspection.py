"""
BookDiagnostics RC70 - Voice Status Retention Inspection.

Inspeciona a politica RC68 sem criar, alterar ou remover arquivos.
Nao inicia audio e nao altera Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from analysis.replay.book_diagnostics_voice_status_retention import (
    BookDiagnosticsVoiceStatusRetentionManager,
)


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionInspection:
    version: str
    directory: str
    prefix: str
    keep: int
    directory_exists: bool
    existing_files: tuple[str, ...]
    retained_files: tuple[str, ...]
    would_remove_files: tuple[str, ...]
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionInspector:
    VERSION = "RC70-VOICE-STATUS-RETENTION-INSPECTION"

    def inspect(
        self,
        directory,
        *,
        keep: int = 20,
        prefix: str = "voice_status",
    ) -> VoiceStatusRetentionInspection:
        if int(keep) < 1:
            raise ValueError("RC70 keep must be >= 1")

        safe_prefix = BookDiagnosticsVoiceStatusRetentionManager._validate_prefix(prefix)
        folder = Path(directory).expanduser().resolve()
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

        retained = candidates[: int(keep)]
        would_remove = candidates[int(keep) :]

        return VoiceStatusRetentionInspection(
            version=self.VERSION,
            directory=str(folder),
            prefix=safe_prefix,
            keep=int(keep),
            directory_exists=exists,
            existing_files=tuple(str(path) for path in candidates),
            retained_files=tuple(str(path) for path in retained),
            would_remove_files=tuple(str(path) for path in would_remove),
        )
