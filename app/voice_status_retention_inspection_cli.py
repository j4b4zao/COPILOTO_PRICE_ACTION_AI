"""
BookDiagnostics RC72 - Voice Status Retention Inspection CLI.

CLI somente leitura para inspecionar a politica RC70/RC71.
Nao cria diretorio, nao gera snapshot, nao remove arquivos e nao executa audio.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspeciona a retencao de snapshots de status de voz sem modificar arquivos"
    )
    parser.add_argument("directory", help="Diretorio contendo snapshots voice_status_*.json")
    parser.add_argument("--keep", type=int, default=20, help="Quantidade de snapshots que seriam mantidos")
    parser.add_argument("--prefix", default="voice_status", help="Prefixo dos snapshots a inspecionar")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # RC72 e estritamente observacional. Mantemos o servico desativado e backend nulo.
    config = VoiceConfig(enabled=False, backend="NULL_TTS")
    system = SystemInitializer(voice_config=config).inicializar()
    inspection = system.voice.inspect_status_retention(
        args.directory,
        keep=int(args.keep),
        prefix=str(args.prefix).strip(),
    )

    print("=== VOICE STATUS RETENTION INSPECTION ===")
    print(f"DIRECTORY: {inspection.directory}")
    print(f"DIRECTORY_EXISTS: {inspection.directory_exists}")
    print(f"PREFIX: {inspection.prefix}")
    print(f"KEEP: {inspection.keep}")
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
