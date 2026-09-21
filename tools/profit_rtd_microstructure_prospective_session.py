"""Sessao prospectiva passiva de microestrutura sobre RC54.3.2.

Reutiliza o warm-up e a janela sincronizada existentes. O recorder de
microestrutura e limpo ao final do warm-up para que o artefato prospectivo
contenha somente ciclos da janela principal. Nenhum resultado retroalimenta
Score, Risk, Decision, Alert ou execucao.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import tools.profit_rtd_rc54_3_2_warmed_session as base
from analysis.replay.microstructure_confluence_session_report import (
    MicrostructureConfluenceSessionReporter,
)


STAGE = "RC1-PROSPECTIVE-MICROSTRUCTURE-EVIDENCE"


def _safety() -> dict:
    return {
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
    }


def run_session(
    symbol,
    *,
    cycles=600,
    interval=0.25,
    max_warmup_cycles=4800,
    output_dir=None,
    sleeper=None,
):
    previous_warm_history = base.warm_history
    active_pipeline = None

    def warm_history_without_replay_leak(*args, **kwargs):
        nonlocal active_pipeline
        warm = previous_warm_history(*args, **kwargs)
        active_pipeline = warm.get("pipeline") if isinstance(warm, dict) else None
        recorder = getattr(active_pipeline, "microstructure_confluence_replay", None)
        if recorder is not None:
            recorder.clear()
        return warm

    base.warm_history = warm_history_without_replay_leak
    try:
        kwargs = {
            "cycles": cycles,
            "interval": interval,
            "max_warmup_cycles": max_warmup_cycles,
            "output_dir": output_dir,
        }
        if sleeper is not None:
            kwargs["sleeper"] = sleeper
        result = base.run_warmed_session(symbol, **kwargs)
    finally:
        base.warm_history = previous_warm_history

    recorder = getattr(active_pipeline, "microstructure_confluence_replay", None)
    samples = [sample.to_dict() for sample in getattr(recorder, "samples", ())]
    report = MicrostructureConfluenceSessionReporter().build(recorder).to_dict() if recorder is not None else {}

    evidence = {
        "stage": STAGE,
        "source_analyzable_samples": int(result.get("analyzable_samples", 0) or 0),
        "captured_samples": len(samples),
        "sample_count_matches_source": len(samples) == int(result.get("analyzable_samples", 0) or 0),
        "report": report,
        "samples": samples,
        **_safety(),
    }
    result["prospective_microstructure"] = evidence
    result.update(_safety())

    output_path = result.get("output_path")
    if output_path:
        path = Path(output_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["prospective_microstructure"] = evidence
        payload.update(_safety())
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Coleta prospectiva passiva PA x Order Flow x Book."
    )
    parser.add_argument("symbol")
    parser.add_argument("--cycles", type=int, default=600)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--max-warmup-cycles", type=int, default=4800)
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)

    result = run_session(
        args.symbol,
        cycles=args.cycles,
        interval=args.interval,
        max_warmup_cycles=args.max_warmup_cycles,
        output_dir=args.output_dir,
    )
    evidence = result["prospective_microstructure"]
    print("PROSPECTIVE_MICROSTRUCTURE=" + str(result.get("status")))
    print("data_ready=" + str(result.get("data_ready")))
    print("captured_samples=" + str(evidence["captured_samples"]))
    print("sample_count_matches_source=" + str(evidence["sample_count_matches_source"]))
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("risk_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("alert_influence_allowed=False")
    print("order_execution_allowed=False")
    if result.get("output_path"):
        print("output_path=" + str(result["output_path"]))
    return 0 if result.get("status") == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
