"""
BookDiagnostics RC75 - Voice Status Retention Health CLI.

CLI somente leitura para exibir o resumo RC73/RC74 da retencao de snapshots.
Nao cria, grava ou remove arquivos e nao possui capacidade de audio.
"""

from __future__ import annotations

import argparse

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Saude da retencao dos snapshots de status de voz"
    )
    parser.add_argument("directory", help="Diretorio a inspecionar")
    parser.add_argument("--keep", type=int, default=20, help="Quantidade maxima esperada de snapshots")
    parser.add_argument("--prefix", default="voice_status", help="Prefixo dos snapshots")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = VoiceConfig(enabled=False, backend="NULL_TTS")
    system = SystemInitializer(voice_config=config).inicializar()

    report = system.voice.retention_health(
        args.directory,
        keep=int(args.keep),
        prefix=str(args.prefix),
    )

    print("=== VOICE STATUS RETENTION HEALTH ===")
    print(f"STATUS: {report.status}")
    print(f"SUMMARY: {report.summary}")
    print(f"DIRECTORY: {report.directory}")
    print(f"DIRECTORY_EXISTS: {report.directory_exists}")
    print(f"PREFIX: {report.prefix}")
    print(f"KEEP: {report.keep}")
    print(f"EXISTING: {report.existing_count}")
    print(f"RETAINED: {report.retained_count}")
    print(f"EXCESS: {report.excess_count}")
    print(f"READONLY: {report.readonly}")

    return 2 if report.status == "OVER_LIMIT" else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
