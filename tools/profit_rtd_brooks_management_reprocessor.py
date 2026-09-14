"""
tools/profit_rtd_brooks_management_reprocessor.py

Reprocessamento offline e research-only da camada Brooks de gerenciamento.

Objetivo:
- ler sessoes RC54.3.2 Brooks ja persistidas;
- preservar os arquivos-fonte;
- reaplicar Stop/Target -> Trailing sobre candle_evidence persistido;
- gravar copias enriquecidas em outro diretorio;
- nao acessar Profit, Excel, RTD, RiskManager, Score, Decision, Alert ou execucao.

O processamento reutiliza exatamente o helper do runner Brooks atual para
manter o mesmo contrato de historico e revisoes de candle.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from tools.profit_rtd_rc54_3_2_brooks_warmed_session import (
    _enrich_management_after_candle_evidence,
)


def _safety():
    return {
        "brooks_management_reprocessed_offline": True,
        "brooks_management_research_only": True,
        "brooks_management_observational_only": True,
        "brooks_management_predictive_claim_allowed": False,
        "brooks_management_score_influence_allowed": False,
        "brooks_management_risk_influence_allowed": False,
        "brooks_management_decision_influence_allowed": False,
        "brooks_management_alert_influence_allowed": False,
        "brooks_management_order_execution_allowed": False,
    }


def reprocess_payload(payload):
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")

    enriched = deepcopy(payload)
    enriched = _enrich_management_after_candle_evidence(enriched)
    enriched.update(_safety())
    return enriched


def reprocess_file(source_path, output_dir):
    source = Path(source_path)
    destination_dir = Path(output_dir)

    if not source.is_file():
        raise FileNotFoundError(str(source))

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name

    payload = json.loads(source.read_text(encoding="utf-8"))
    enriched = reprocess_payload(payload)

    destination.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "source": str(source),
        "output": str(destination),
        "sample_count": len(enriched.get("samples") or []),
        "management_postprocessed": bool(
            enriched.get(
                "brooks_management_postprocessed_after_candle_evidence"
            )
        ),
        **_safety(),
    }


def reprocess_many(paths, output_dir):
    reports = [
        reprocess_file(path, output_dir)
        for path in paths
    ]

    return {
        "status": "COMPLETED",
        "processed_files": len(reports),
        "output_dir": str(Path(output_dir)),
        "files": reports,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reprocessa sessoes Brooks para Stop/Target + Trailing."
    )
    parser.add_argument("paths", nargs="+")
    parser.add_argument(
        "--output-dir",
        required=True,
    )
    args = parser.parse_args(argv)

    report = reprocess_many(args.paths, args.output_dir)

    print("status=", report["status"])
    print("processed_files=", report["processed_files"])
    print("output_dir=", report["output_dir"])

    for item in report["files"]:
        print(
            "file=",
            Path(item["output"]).name,
            "samples=",
            item["sample_count"],
            "management_postprocessed=",
            item["management_postprocessed"],
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
