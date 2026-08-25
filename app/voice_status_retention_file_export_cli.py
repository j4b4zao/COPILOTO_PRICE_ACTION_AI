"""
BookDiagnostics RC86 - Voice Status Retention File Export CLI.

CLI explicito para persistir o envelope RC83 de retencao em arquivo JSON usando RC85.
Nao possui opcoes de fala, nao executa audio e nao conecta ao loop principal.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta o status de retencao da integracao de voz do COPILOTO PRICE ACTION AI para JSON"
    )
    parser.add_argument("source_directory", help="Diretorio contendo os snapshots de voz")
    parser.add_argument("destination", help="Caminho de destino .json")
    parser.add_argument("--keep", type=int, default=20)
    parser.add_argument("--prefix", default="voice_status")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_directory = Path(str(args.source_directory)).expanduser()
    destination = Path(str(args.destination)).expanduser()

    config = VoiceConfig(enabled=False, backend="NULL_TTS")
    system = SystemInitializer(voice_config=config).inicializar()
    result = system.voice.export_retention_status_file(
        source_directory,
        destination,
        keep=int(args.keep),
        prefix=str(args.prefix),
    )

    print("=== VOICE STATUS RETENTION FILE EXPORT ===")
    print(f"PATH: {result.path}")
    print(f"STATUS: {result.status}")
    print(f"SCHEMA: {result.schema}")
    print(f"BYTES: {result.bytes_written}")
    print(f"READONLY: {result.readonly}")

    return 0 if result.status in {"EMPTY", "WITHIN_LIMIT"} else 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
