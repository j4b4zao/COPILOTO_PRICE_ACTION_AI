"""
BookDiagnostics RC95 - Retention Export Rotation Health CLI.

CLI somente leitura para exibir o resumo RC93/RC94 da segunda serie historica.
Nao cria, grava ou remove arquivos e nao possui capacidade de audio.
"""

from __future__ import annotations

import argparse

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Saude da segunda serie historica do status de retencao de voz"
    )
    parser.add_argument("export_directory", help="Diretorio da serie voice_retention_status_*.json")
    parser.add_argument(
        "--export-keep",
        type=int,
        default=20,
        help="Quantidade maxima esperada de exports historicos",
    )
    parser.add_argument(
        "--export-prefix",
        default="voice_retention_status",
        help="Prefixo da segunda serie historica",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = VoiceConfig(enabled=False, backend="NULL_TTS")
    system = SystemInitializer(voice_config=config).inicializar()

    report = system.voice.retention_status_exports_health(
        args.export_directory,
        export_keep=int(args.export_keep),
        export_prefix=str(args.export_prefix),
    )

    print("=== VOICE RETENTION STATUS EXPORTS HEALTH ===")
    print(f"STATUS: {report.status}")
    print(f"SUMMARY: {report.summary}")
    print(f"EXPORT_DIRECTORY: {report.export_directory}")
    print(f"DIRECTORY_EXISTS: {report.directory_exists}")
    print(f"EXPORT_PREFIX: {report.export_prefix}")
    print(f"EXPORT_KEEP: {report.export_keep}")
    print(f"EXISTING: {report.existing_count}")
    print(f"RETAINED: {report.retained_count}")
    print(f"WOULD_REMOVE: {report.would_remove_count}")
    print(f"READONLY: {report.readonly}")

    return 2 if report.status == "OVER_LIMIT" else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
