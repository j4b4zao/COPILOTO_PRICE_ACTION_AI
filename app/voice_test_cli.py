"""
BookDiagnostics RC48 - Voice Test CLI.

Utilitario isolado do loop principal do bot para executar diagnostico de voz
e, opcionalmente, um teste real de audio controlado. Nenhuma fala e disparada
sem a flag explicita --speak.
"""

from __future__ import annotations

import argparse
import json

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnostico e teste controlado de voz do COPILOTO PRICE ACTION AI"
    )
    parser.add_argument("--backend", default="NULL_TTS")
    parser.add_argument("--language", default="pt-BR")
    parser.add_argument("--profile", default="BRITISH_CALM_PRECISE_ASSISTANT")
    parser.add_argument("--rate", type=float, default=1.0)
    parser.add_argument("--speak", action="store_true")
    parser.add_argument("--text", default=None)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = VoiceConfig(
        enabled=bool(args.speak),
        backend=str(args.backend).strip().upper(),
        language=str(args.language).strip(),
        voice_profile=str(args.profile).strip(),
        speech_rate=float(args.rate),
    )
    system = SystemInitializer(voice_config=config).inicializar()
    diagnostics = system.voice.diagnostics()
    print("=== VOICE DIAGNOSTICS ===")
    print(json.dumps(diagnostics.to_dict(), ensure_ascii=False, indent=2))

    if not args.speak:
        print("Audio real nao solicitado. Use --speak para teste explicito.")
        return 0
    if not diagnostics.ready_for_real_audio:
        print("Teste de audio bloqueado: diagnostico nao esta READY.")
        return 2

    result = system.voice.test_audio(text=args.text)
    print("=== CONTROLLED AUDIO TEST ===")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.completed else 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
