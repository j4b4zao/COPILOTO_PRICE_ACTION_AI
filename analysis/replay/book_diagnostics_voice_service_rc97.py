"""
BookDiagnostics RC97 - Retention Export Rotation Dashboard Service Integration.

Extensao fina do servico RC94 para expor a projecao readonly RC96 da segunda
serie historica, sem duplicar regras, sem mutacao de arquivos e sem audio.
"""

from __future__ import annotations

from analysis.replay.book_diagnostics_voice_service_rc94 import BookDiagnosticsVoiceServiceRC94
from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_dashboard_projection import (
    BookDiagnosticsVoiceStatusRetentionExportRotationDashboardProjector,
)


class BookDiagnosticsVoiceServiceRC97(BookDiagnosticsVoiceServiceRC94):
    """Adiciona apenas a fachada readonly RC97 sobre RC93 -> RC96."""

    def retention_status_exports_dashboard_projection(
        self,
        export_directory,
        *,
        export_keep: int = 20,
        export_prefix: str = "voice_retention_status",
    ):
        health = self.retention_status_exports_health(
            export_directory,
            export_keep=export_keep,
            export_prefix=export_prefix,
        )
        return BookDiagnosticsVoiceStatusRetentionExportRotationDashboardProjector().project(health)
