"""
BookDiagnostics RC57 - Voice Health CLI.

CLI somente leitura para exibir o health report RC56 no terminal.
Nao possui --speak, nao executa teste de audio e nao conecta ao loop principal.
"""

from __future__ import annotations

import argparse
import json

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Status de saude da integracao de voz do COPILOTO PRICE ACTION AI"
    )
    parser.add_argument("--enabled", action="store_true", help="Avalia o servico como habilitado sem iniciar fala")
    parser.add_argument("--backend", default="NULL_TTS")
    parser.add_argument("--language", default="pt-BR")
    parser.add_argument("--profile", default="BRITISH_CALM_PRECISE_ASSISTANT")
    parser.add_argument("--rate", type=float, default=1.0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = VoiceConfig(
        enabled=bool(args.enabled),
        backend=str(args.backend).strip().upper(),
        language=str(args.language).strip(),
        voice_profile=str(args.profile).strip(),
        speech_rate=float(args.rate),
    )
    system = SystemInitializer(voice_config=config).inicializar()
    report = system.voice.health_report()

    if args.as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("=== VOICE HEALTH ===")
        print(f"STATUS: {report.status}")
        print(f"SUMMARY: {report.summary}")
        print(f"BACKEND: {report.backend}")
        print(f"BACKEND_HEALTHY: {report.backend_healthy}")
        print(f"OPERATIONAL_VOICE_ALLOWED: {report.operational_voice_allowed}")
        print(f"READINESS_REASON: {report.readiness_reason}")

    return 0 if report.status in {"DISABLED", "READY", "TEST_REQUIRED", "DIAGNOSTICS_PENDING"} else 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
