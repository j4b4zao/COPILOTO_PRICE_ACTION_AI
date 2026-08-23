"""
BookDiagnostics RC68 - Voice Status Export Rotation/Retention.

Mantem um numero limitado de snapshots JSON de status de voz, apagando somente
arquivos que sigam um prefixo explicito. Nao inicia audio e nao altera Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import re


@dataclass(slots=True, frozen=True)
class VoiceStatusRetentionResult:
    version: str
    directory: str
    prefix: str
    keep: int
    current_file: str
    retained_files: tuple[str, ...]
    removed_files: tuple[str, ...]
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceStatusRetentionManager:
    VERSION = "RC68-VOICE-STATUS-EXPORT-RETENTION"

    def export_and_rotate(
        self,
        *,
        voice_service,
        directory,
        keep: int = 20,
        prefix: str = "voice_status",
        generated_at: datetime | None = None,
    ) -> VoiceStatusRetentionResult:
        if int(keep) < 1:
            raise ValueError("RC68 keep must be >= 1")
        safe_prefix = self._validate_prefix(prefix)
        folder = Path(directory).expanduser().resolve()
        folder.mkdir(parents=True, exist_ok=True)

        instant = generated_at or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        instant = instant.astimezone(timezone.utc)
        stamp = instant.strftime("%Y%m%dT%H%M%S%fZ")
        target = folder / f"{safe_prefix}_{stamp}.json"

        write_result = voice_service.export_status_file(target, generated_at=instant)
        current = Path(write_result.path).resolve()

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
        removed = candidates[int(keep) :]
        for path in removed:
            path.unlink(missing_ok=True)

        return VoiceStatusRetentionResult(
            version=self.VERSION,
            directory=str(folder),
            prefix=safe_prefix,
            keep=int(keep),
            current_file=str(current),
            retained_files=tuple(str(path) for path in retained),
            removed_files=tuple(str(path) for path in removed),
        )

    @staticmethod
    def _validate_prefix(prefix: str) -> str:
        value = str(prefix or "").strip()
        if not value:
            raise ValueError("RC68 prefix cannot be empty")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("RC68 prefix may contain only letters, numbers, _ and -")
        return value
