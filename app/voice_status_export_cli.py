"""
BookDiagnostics RC67 - Voice Status Export CLI.

CLI explicito para persistir o envelope RC64 em arquivo JSON usando RC66.
Nao possui opcoes de fala, nao executa audio e nao conecta ao loop principal.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta o status da integracao de voz do COPILOTO PRICE ACTION AI para JSON"
    )
    parser.add_argument("destination", help="Caminho de destino .json")
    parser.add_argument("--enabled", action="store_true", help="Avalia o servico como habilitado sem iniciar fala")
    parser.add_argument("--backend", default="NULL_TTS")
    parser.add_argument("--language", default="pt-BR")
    parser.add_argument("--profile", default="BRITISH_CALM_PRECISE_ASSISTANT")
    parser.add_argument("--rate", type=float, default=1.0)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    destination = Path(str(args.destination)).expanduser()

    config = VoiceConfig(
        enabled=bool(args.enabled),
        backend=str(args.backend).strip().upper(),
        language=str(args.language).strip(),
        voice_profile=str(args.profile).strip(),
        speech_rate=float(args.rate),
    )
    system = SystemInitializer(voice_config=config).inicializar()
    result = system.voice.export_status_file(destination)

    print("=== VOICE STATUS EXPORT ===")
    print(f"PATH: {result.path}")
    print(f"STATUS: {result.status}")
    print(f"SCHEMA: {result.schema}")
    print(f"BYTES: {result.bytes_written}")
    print(f"READONLY: {result.readonly}")

    return 0 if result.status in {"DISABLED", "READY", "TEST_REQUIRED", "DIAGNOSTICS_PENDING"} else 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
