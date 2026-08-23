"""
BookDiagnostics RC94 - Retention Export Rotation Health Service Integration.

Extensao fina do servico RC91 para expor o resumo readonly RC93 da segunda
serie historica, sem duplicar regras, sem mutacao de arquivos e sem audio.
"""

from __future__ import annotations

from analysis.replay.book_diagnostics_voice_service_rc91 import BookDiagnosticsVoiceServiceRC91
from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_health import (
    BookDiagnosticsVoiceStatusRetentionExportRotationHealthReporter,
)


class BookDiagnosticsVoiceServiceRC94(BookDiagnosticsVoiceServiceRC91):
    """Adiciona apenas a fachada readonly RC94 sobre RC90 -> RC93."""

    def retention_status_exports_health(
        self,
        export_directory,
        *,
        export_keep: int = 20,
        export_prefix: str = "voice_retention_status",
    ):
        inspection = self.inspect_retention_status_exports(
            export_directory,
            export_keep=export_keep,
            export_prefix=export_prefix,
        )
        return BookDiagnosticsVoiceStatusRetentionExportRotationHealthReporter().build(inspection)
