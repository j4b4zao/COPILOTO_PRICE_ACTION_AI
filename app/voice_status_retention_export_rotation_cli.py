"""
BookDiagnostics RC89 - Voice Retention Status Export Rotation CLI.

CLI explicito para gerar a serie historica rotacionada do proprio status de
retencao via RC88. Voz permanece desativada e nao ha integracao com app.main.
"""

from __future__ import annotations

import argparse

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera historico rotacionado do status de retencao da voz"
    )
    parser.add_argument("source_directory", help="Diretorio dos snapshots normais de voz")
    parser.add_argument("export_directory", help="Diretorio da serie historica de retencao")
    parser.add_argument("--source-keep", type=int, default=20)
    parser.add_argument("--source-prefix", default="voice_status")
    parser.add_argument("--export-keep", type=int, default=20)
    parser.add_argument("--export-prefix", default="voice_retention_status")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = VoiceConfig(enabled=False, backend="NULL_TTS")
    system = SystemInitializer(voice_config=config).inicializar()
    result = system.voice.export_retention_status_rotated(
        args.source_directory,
        args.export_directory,
        source_keep=int(args.source_keep),
        source_prefix=str(args.source_prefix).strip(),
        export_keep=int(args.export_keep),
        export_prefix=str(args.export_prefix).strip(),
    )

    print("=== VOICE RETENTION STATUS EXPORT ROTATION ===")
    print(f"SOURCE_DIRECTORY: {result.source_directory}")
    print(f"EXPORT_DIRECTORY: {result.export_directory}")
    print(f"SOURCE_PREFIX: {result.source_prefix}")
    print(f"EXPORT_PREFIX: {result.export_prefix}")
    print(f"SOURCE_KEEP: {result.source_keep}")
    print(f"EXPORT_KEEP: {result.export_keep}")
    print(f"CURRENT_FILE: {result.current_file}")
    print(f"RETAINED: {len(result.retained_files)}")
    print(f"REMOVED: {len(result.removed_files)}")
    print(f"READONLY: {result.readonly}")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
