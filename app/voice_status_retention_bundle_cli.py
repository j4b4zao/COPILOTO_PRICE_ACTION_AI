"""
BookDiagnostics RC82 - Voice Status Retention Bundle CLI.

CLI somente leitura para exibir o bundle RC80/RC81 em texto ou JSON.
Nao gera snapshot, nao remove arquivos, nao possui --speak e nao conecta ao loop principal.
"""

from __future__ import annotations

import argparse
import json

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from core.system_initializer import SystemInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bundle readonly de retencao dos snapshots de voz do COPILOTO PRICE ACTION AI"
    )
    parser.add_argument("directory", help="Diretorio dos snapshots de status de voz")
    parser.add_argument("--keep", type=int, default=20, help="Quantidade maxima considerada pela politica de retencao")
    parser.add_argument("--prefix", default="voice_status", help="Prefixo controlado dos snapshots")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Exibe o bundle completo em JSON")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = VoiceConfig(enabled=False, backend="NULL_TTS")
    system = SystemInitializer(voice_config=config).inicializar()
    bundle = system.voice.retention_status_bundle(
        args.directory,
        keep=args.keep,
        prefix=args.prefix,
    )
    payload = bundle.to_dict()
    status = str(bundle.health.get("status", ""))

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("=== VOICE STATUS RETENTION BUNDLE ===")
        print(f"STATUS: {status}")
        print(f"READONLY: {bundle.readonly}")
        print("--- INSPECTION ---")
        print(f"DIRECTORY: {bundle.inspection['directory']}")
        print(f"DIRECTORY_EXISTS: {bundle.inspection['directory_exists']}")
        print(f"PREFIX: {bundle.inspection['prefix']}")
        print(f"KEEP: {bundle.inspection['keep']}")
        print(f"EXISTING_FILES: {len(bundle.inspection['existing_files'])}")
        print(f"RETAINED_FILES: {len(bundle.inspection['retained_files'])}")
        print(f"WOULD_REMOVE_FILES: {len(bundle.inspection['would_remove_files'])}")
        print("--- HEALTH ---")
        print(f"SUMMARY: {bundle.health['summary']}")
        print("--- DASHBOARD PROJECTION ---")
        print(f"LABEL: {bundle.dashboard_projection['label']}")
        print("--- DASHBOARD WIDGET ---")
        print(f"TITLE: {bundle.dashboard_widget['title']}")
        print(f"DETAIL: {bundle.dashboard_widget['detail']}")
        print(f"EXCESS_COUNT: {bundle.dashboard_widget['excess_count']}")

    return 2 if status == "OVER_LIMIT" else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
