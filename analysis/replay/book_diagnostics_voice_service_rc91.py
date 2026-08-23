"""
BookDiagnostics RC91 - Retention Export Rotation Inspection Service Integration.

Extensao fina do BookDiagnosticsVoiceService para expor a inspecao readonly RC90
sem duplicar politica, sem criar/remover arquivos e sem qualquer capacidade de audio.
"""

from __future__ import annotations

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService
from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_inspection import (
    BookDiagnosticsVoiceStatusRetentionExportRotationInspector,
)


class BookDiagnosticsVoiceServiceRC91(BookDiagnosticsVoiceService):
    """Adiciona apenas a fachada readonly RC91 sobre o inspector RC90."""

    def inspect_retention_status_exports(
        self,
        export_directory,
        *,
        export_keep: int = 20,
        export_prefix: str = "voice_retention_status",
    ):
        return BookDiagnosticsVoiceStatusRetentionExportRotationInspector().inspect(
            export_directory,
            export_keep=export_keep,
            export_prefix=export_prefix,
        )
