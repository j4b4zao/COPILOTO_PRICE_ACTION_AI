"""
BookDiagnostics RC92 - Voice Retention Export Rotation Inspection CLI.

CLI somente leitura para inspecionar a serie historica RC90/RC91.
Nao cria diretorio, nao gera export, nao remove arquivos e nao executa audio.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspeciona a serie historica do status de retencao sem modificar arquivos"
    )
    parser.add_argument("export_directory", help="Diretorio contendo voice_retention_status_*.json")
    parser.add_argument(
        "--export-keep",
        type=int,
        default=20,
        help="Quantidade de exports historicos que seriam mantidos",
    )
    parser.add_argument(
        "--export-prefix",
        default="voice_retention_status",
        help="Prefixo da serie historica a inspecionar",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = VoiceConfig(enabled=False, backend="NULL_TTS")
    system = SystemInitializer(voice_config=config).inicializar()
    inspection = system.voice.inspect_retention_status_exports(
        args.export_directory,
        export_keep=int(args.export_keep),
        export_prefix=str(args.export_prefix).strip(),
    )

    print("=== VOICE RETENTION STATUS EXPORT INSPECTION ===")
    print(f"DIRECTORY: {inspection.export_directory}")
    print(f"DIRECTORY_EXISTS: {inspection.directory_exists}")
    print(f"PREFIX: {inspection.export_prefix}")
    print(f"KEEP: {inspection.export_keep}")
    print(f"EXISTING: {len(inspection.existing_files)}")
    print(f"RETAINED: {len(inspection.retained_files)}")
    print(f"WOULD_REMOVE: {len(inspection.would_remove_files)}")

    if inspection.existing_files:
        print("--- EXISTING FILES ---")
        for path in inspection.existing_files:
            print(Path(path).name)

    if inspection.would_remove_files:
        print("--- WOULD REMOVE ---")
        for path in inspection.would_remove_files:
            print(Path(path).name)

    print(f"READONLY: {inspection.readonly}")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
