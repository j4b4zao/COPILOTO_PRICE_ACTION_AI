"""
tools/profit_rtd_order_flow_historical_shadow_reprocessor.py

Reprocessador histórico observacional de Order Flow.

Fluxo:
RC54 histórico
    -> filtro de segurança/readiness
    -> RC31 apenas para magnitude dos thresholds
    -> RC35_SIGNED_DELTA para direção
    -> sessões shadow separadas

IMPORTANTE:
- Não altera os JSONs de origem.
- Não usa OOS automaticamente.
- Não usa Brooks automaticamente.
- Não influencia Score, Risk, Decision, Alert ou execução.
- RC31 é usado somente para magnitude dos thresholds.
- Direção é sempre derivada do sinal de recent_delta conforme RC35.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from market_data.order_flow_alignment_calibrator import (
    OrderFlowAlignmentCalibrator,
)
from market_data.order_flow_shadow_calibration import (
    OrderFlowShadowCalibration,
)


STAGE = "ORDER_FLOW_HISTORICAL_SHADOW_REPROCESSOR_V1"
DIRECTION_LOGIC_VERSION = "RC35_SIGNED_DELTA"

OBSERVATIONAL_ONLY = True
SCORE_INFLUENCE_ALLOWED = False
DECISION_INFLUENCE_ALLOWED = False
ORDER_EXECUTION_ALLOWED = False


def _safe_payload(payload: dict) -> bool:
    return (
        payload.get("observational_only") is True
        and payload.get("score_influence_allowed") is False
        and payload.get("decision_influence_allowed") is False
        and payload.get("order_execution_allowed") is False
    )


def _eligible_sample(sample: dict) -> bool:
    return (
        sample.get("data_ready") is True
        and sample.get("context_ready") is True
        and sample.get("delta_status") == "VALID"
        and sample.get("book_status") == "VALID"
        and sample.get("recent_delta") is not None
        and sample.get("dominance") is not None
        and sample.get("imbalance") is not None
        and sample.get("alignment") is not None
    )


def _load_source_sessions(source_dir: Path) -> list[tuple[Path, dict, list[dict]]]:
    sessions: list[tuple[Path, dict, list[dict]]] = []

    for path in sorted(source_dir.glob("profit_rtd_rc54_3_2_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8-sig"))

        if not _safe_payload(payload):
            continue

        eligible = [
            sample
            for sample in payload.get("samples", [])
            if _eligible_sample(sample)
        ]

        if eligible:
            sessions.append((path, payload, eligible))

    return sessions


def _calibrate(
    sessions: list[tuple[Path, dict, list[dict]]],
):
    samples = []

    for _, _, eligible in sessions:
        samples.extend(
            {
                "dominance": float(sample["dominance"]),
                "imbalance": float(sample["imbalance"]),
            }
            for sample in eligible
        )

    return OrderFlowAlignmentCalibrator().evaluate(samples)


def _build_context(sample: dict):
    return SimpleNamespace(
        status="READY",
        directional_alignment=str(sample["alignment"]),
        recent_delta=float(sample["recent_delta"]),
        delta_dominance=abs(float(sample["dominance"])),
        book_imbalance=float(sample["imbalance"]),
    )


def _reprocess_session(
    source_path: Path,
    source_payload: dict,
    samples: list[dict],
    *,
    delta_threshold: float,
    book_threshold: float,
) -> dict:

    shadow = OrderFlowShadowCalibration(
        delta_threshold=delta_threshold,
        book_threshold=book_threshold,
    )

    output_samples = []

    official_counts = {
        "BULLISH_ALIGNED": 0,
        "BEARISH_ALIGNED": 0,
        "DIVERGENT": 0,
        "NEUTRAL": 0,
    }

    shadow_counts = {
        "BULLISH_ALIGNED": 0,
        "BEARISH_ALIGNED": 0,
        "DIVERGENT": 0,
        "NEUTRAL": 0,
    }

    changed_count = 0

    for sample in samples:
        result = shadow.evaluate(_build_context(sample))

        official_counts[result.official_alignment] = (
            official_counts.get(result.official_alignment, 0) + 1
        )

        shadow_counts[result.shadow_alignment] = (
            shadow_counts.get(result.shadow_alignment, 0) + 1
        )

        if result.changed:
            changed_count += 1

        output_samples.append(
            {
                "cycle": sample.get("cycle"),
                "timestamp": sample.get("timestamp"),
                "status": "READY",
                "official_alignment": result.official_alignment,
                "shadow_alignment": result.shadow_alignment,
                "changed": result.changed,
                "recent_delta": result.recent_delta,
                "dominance": result.dominance,
                "imbalance": result.imbalance,
                "delta_threshold": result.delta_threshold,
                "book_threshold": result.book_threshold,
                "direction_logic_version": DIRECTION_LOGIC_VERSION,
                "observational_only": True,
                "score_influence_allowed": False,
                "decision_influence_allowed": False,
                "order_execution_allowed": False,
            }
        )

    return {
        "stage": STAGE,
        "status": "COMPLETED",
        "symbol": source_payload.get("symbol", ""),
        "source_file": source_path.name,
        "source_phase": source_payload.get("phase"),
        "historical_reprocessing": True,
        "oos_included": False,
        "brooks_included": False,
        "completed_cycles": len(output_samples),
        "delta_threshold": float(delta_threshold),
        "book_threshold": float(book_threshold),
        "direction_logic_version": DIRECTION_LOGIC_VERSION,
        "official_counts": official_counts,
        "shadow_counts": shadow_counts,
        "changed_count": changed_count,
        "observational_only": OBSERVATIONAL_ONLY,
        "score_influence_allowed": SCORE_INFLUENCE_ALLOWED,
        "decision_influence_allowed": DECISION_INFLUENCE_ALLOWED,
        "order_execution_allowed": ORDER_EXECUTION_ALLOWED,
        "samples": output_samples,
    }


def run(
    source_dir: str,
    output_dir: str,
) -> dict:

    source = Path(source_dir).expanduser().resolve()
    target = Path(output_dir).expanduser().resolve()

    if not source.is_dir():
        raise ValueError(f"source_dir invalido: {source}")

    target.mkdir(parents=True, exist_ok=True)

    sessions = _load_source_sessions(source)

    if not sessions:
        raise ValueError("nenhuma sessao historica elegivel")

    calibration = _calibrate(sessions)

    delta_threshold = calibration.suggested_delta_threshold
    book_threshold = calibration.suggested_book_threshold

    outputs = []

    for source_path, source_payload, samples in sessions:

        report = _reprocess_session(
            source_path,
            source_payload,
            samples,
            delta_threshold=delta_threshold,
            book_threshold=book_threshold,
        )

        output_path = target / f"shadow_rc35_{source_path.name}"

        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        outputs.append(
            {
                "source_file": source_path.name,
                "output_file": str(output_path),
                "samples": report["completed_cycles"],
                "shadow_counts": report["shadow_counts"],
                "changed_count": report["changed_count"],
            }
        )

    return {
        "stage": STAGE,
        "status": "COMPLETED",
        "source_dir": str(source),
        "output_dir": str(target),
        "sessions": len(outputs),
        "samples": sum(item["samples"] for item in outputs),
        "delta_threshold": delta_threshold,
        "book_threshold": book_threshold,
        "direction_logic_version": DIRECTION_LOGIC_VERSION,
        "rc31_candidate_direction_counts_used": False,
        "oos_included": False,
        "brooks_included": False,
        "observational_only": OBSERVATIONAL_ONLY,
        "score_influence_allowed": SCORE_INFLUENCE_ALLOWED,
        "decision_influence_allowed": DECISION_INFLUENCE_ALLOWED,
        "order_execution_allowed": ORDER_EXECUTION_ALLOWED,
        "calibration": calibration.to_dict(),
        "session_reports": outputs,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Reprocessa historico RC54 para shadow RC35 "
            "sem qualquer efeito operacional."
        )
    )

    parser.add_argument(
        "--source-dir",
        default=r"C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_rc54_3_2",
    )

    parser.add_argument(
        "--output-dir",
        default=r"C:\COPILOTO_PRICE_ACTION_AI\data\order_flow_historical_shadow_rc35",
    )

    parser.add_argument(
        "--report",
        default=r"C:\COPILOTO_PRICE_ACTION_AI\data\order_flow_historical_shadow_rc35_report.json",
    )

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        report = run(
            source_dir=args.source_dir,
            output_dir=args.output_dir,
        )

        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)

        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    except Exception as exc:
        print("ORDER_FLOW_HISTORICAL_SHADOW_REPROCESSOR=ERROR")
        print(f"reason={type(exc).__name__}:{exc}")
        return 1

    print("ORDER_FLOW_HISTORICAL_SHADOW_REPROCESSOR=COMPLETED")
    print(f"sessions={report['sessions']}")
    print(f"samples={report['samples']}")
    print(f"delta_threshold={report['delta_threshold']}")
    print(f"book_threshold={report['book_threshold']}")
    print(f"direction_logic_version={report['direction_logic_version']}")
    print(
        "rc31_candidate_direction_counts_used="
        f"{report['rc31_candidate_direction_counts_used']}"
    )
    print("oos_included=False")
    print("brooks_included=False")
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    print(f"report={report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
