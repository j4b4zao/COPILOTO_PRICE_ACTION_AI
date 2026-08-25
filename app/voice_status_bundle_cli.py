"""
BookDiagnostics RC63 - Voice Status Bundle CLI.

CLI somente leitura para exibir o bundle RC62 em texto ou JSON.
Nao possui --speak, nao executa teste de audio e nao conecta ao loop principal.
"""

from __future__ import annotations

import argparse
import json

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bundle de status da integracao de voz do COPILOTO PRICE ACTION AI"
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
    bundle = system.voice.status_bundle()
    payload = bundle.to_dict()

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("=== VOICE STATUS BUNDLE ===")
        print(f"STATUS: {bundle.status}")
        print(f"READONLY: {bundle.readonly}")
        print("--- HEALTH REPORT ---")
        print(f"SUMMARY: {bundle.health_report['summary']}")
        print(f"BACKEND: {bundle.health_report['backend']}")
        print(f"BACKEND_HEALTHY: {bundle.health_report['backend_healthy']}")
        print(f"READINESS_REASON: {bundle.health_report['readiness_reason']}")
        print("--- DASHBOARD PROJECTION ---")
        print(f"LABEL: {bundle.dashboard_projection['label']}")
        print("--- DASHBOARD WIDGET ---")
        print(f"TITLE: {bundle.dashboard_widget['title']}")
        print(f"DETAIL: {bundle.dashboard_widget['detail']}")
        print(f"OPERATIONAL_VOICE_ALLOWED: {bundle.dashboard_widget['operational_voice_allowed']}")

    return 0 if bundle.status in {"DISABLED", "READY", "TEST_REQUIRED", "DIAGNOSTICS_PENDING"} else 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
