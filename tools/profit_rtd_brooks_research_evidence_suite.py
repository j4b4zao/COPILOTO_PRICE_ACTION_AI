"""Suite offline de evidencias Brooks research-only.

Agrega auditores EXACT_CANDLE ja existentes para as hipoteses Brooks sem
promover hipotese e sem alterar Score, Risk, Decision, Alert ou execucao.

A suite mantem selecao e OOS explicitamente separados. O modo OOS exige um
cutoff informado e rejeita sessoes cujo inicio nao seja estritamente posterior
ao cutoff.

Os auditores Brooks foram criados em etapas diferentes e nao possuem todos a
mesma API publica. Esta suite normaliza esses contratos sem alterar nenhum dos
auditores ja validados:

- usa ``audit(paths)`` quando o modulo expoe auditoria por caminhos;
- usa ``audit_sessions(payloads)`` para auditoria multi-session por payload;
- usa ``audit_payload(payload)`` quando apenas uma sessao foi fornecida.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import tools.profit_rtd_brooks_breakout_pullback_audit as breakout_pullback_audit
import tools.profit_rtd_brooks_failed_breakout_audit as failed_breakout_audit
import tools.profit_rtd_brooks_major_trend_reversal_audit as major_trend_reversal_audit
import tools.profit_rtd_brooks_trading_range_reversal_audit as trading_range_reversal_audit
import tools.profit_rtd_brooks_trend_pullback_audit as trend_pullback_audit
import tools.profit_rtd_brooks_wedge_three_pushes_audit as wedge_three_pushes_audit
from tools.profit_rtd_price_action_evidence_audit import _session_interval


MANAGEMENT_RESEARCH = "BROOKS_STOP_TARGET_RULES_V1"


def _safety():
    return {
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def _load(path):
    source = Path(path)
    return source, json.loads(source.read_text(encoding="utf-8"))


def _call_auditor(module, paths):
    """Normaliza as APIs historicas dos auditores Brooks.

    A funcao recebe caminhos aceitos pela suite e devolve o relatorio nativo
    do auditor. Nenhuma semantica do auditor e reinterpretada aqui.
    """
    normalized_paths = [str(Path(path)) for path in paths]

    audit_fn = getattr(module, "audit", None)
    if callable(audit_fn):
        return audit_fn(normalized_paths)

    payloads = [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for path in normalized_paths
    ]

    audit_sessions_fn = getattr(module, "audit_sessions", None)
    audit_payload_fn = getattr(module, "audit_payload", None)

    if len(payloads) == 1 and callable(audit_payload_fn):
        return audit_payload_fn(payloads[0])

    if callable(audit_sessions_fn):
        return audit_sessions_fn(payloads)

    if callable(audit_payload_fn):
        return {
            "status": "MULTI_SESSION_ADAPTER_COMPLETED",
            "eligible_sessions": len(payloads),
            "sessions": [audit_payload_fn(payload) for payload in payloads],
            "hypothesis_freeze_allowed": False,
            **_safety(),
        }

    raise AttributeError(
        f"Auditor module {getattr(module, '__name__', module)!r} exposes no "
        "supported audit contract"
    )


def _auditor(module):
    def run(paths):
        return _call_auditor(module, paths)

    return run


AUDITORS = {
    "BROOKS_BREAKOUT_PULLBACK_V1": _auditor(breakout_pullback_audit),
    "BROOKS_TREND_PULLBACK_V1": _auditor(trend_pullback_audit),
    "BROOKS_FAILED_BREAKOUT_V1": _auditor(failed_breakout_audit),
    "BROOKS_MAJOR_TREND_REVERSAL_V1": _auditor(major_trend_reversal_audit),
    "BROOKS_WEDGE_THREE_PUSHES_V1": _auditor(wedge_three_pushes_audit),
    "BROOKS_TRADING_RANGE_REVERSAL_V1": _auditor(trading_range_reversal_audit),
}


def _interval_from_payload(payload):
    samples = payload.get("samples") if isinstance(payload, dict) else None
    if not isinstance(samples, list):
        return None
    return _session_interval(samples)


def _parse_cutoff(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.timestamp()
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError as exc:
        raise ValueError("invalid ISO cutoff") from exc


def _eligible_paths(paths, *, mode, selection_cutoff=None):
    cutoff = _parse_cutoff(selection_cutoff)
    accepted = []
    rejected = []
    intervals = []

    for raw in paths:
        path, payload = _load(raw)
        interval = _interval_from_payload(payload)
        if interval is None:
            rejected.append({
                "session": path.name,
                "reason": "SESSION_INTERVAL_UNAVAILABLE",
            })
            continue

        if mode == "OOS":
            if cutoff is None:
                rejected.append({
                    "session": path.name,
                    "reason": "SELECTION_CUTOFF_REQUIRED_FOR_OOS",
                })
                continue
            if interval[0] <= cutoff:
                rejected.append({
                    "session": path.name,
                    "reason": "SESSION_NOT_STRICTLY_AFTER_SELECTION_CUTOFF",
                })
                continue

        overlap = next((
            prior_name
            for prior_name, prior_interval in intervals
            if interval[0] <= prior_interval[1]
            and prior_interval[0] <= interval[1]
        ), None)
        if overlap is not None:
            rejected.append({
                "session": path.name,
                "reason": "TEMPORAL_OVERLAP",
                "overlaps_with": overlap,
            })
            continue

        accepted.append(str(path))
        intervals.append((path.name, interval))

    return accepted, rejected


def build_report(paths, *, mode="SELECTION", selection_cutoff=None):
    paths = list(paths)
    mode = str(mode or "SELECTION").strip().upper()
    if mode not in {"SELECTION", "OOS"}:
        raise ValueError("mode must be SELECTION or OOS")

    accepted, rejected = _eligible_paths(
        paths,
        mode=mode,
        selection_cutoff=selection_cutoff,
    )

    setup_reports = {}
    if accepted:
        for setup_name, auditor in AUDITORS.items():
            setup_reports[setup_name] = auditor(accepted)
    else:
        for setup_name in AUDITORS:
            setup_reports[setup_name] = {
                "status": "NO_ELIGIBLE_SESSIONS",
                "eligible_sessions": 0,
                "complete_sequences": 0,
                "hypothesis_freeze_allowed": False,
                **_safety(),
            }

    setup_reports[MANAGEMENT_RESEARCH] = {
        "status": "CLASSIFIER_ONLY_NO_EXACT_AUDITOR",
        "eligible_sessions": len(accepted),
        "hypothesis_freeze_allowed": False,
        "reasons": ["STOP_TARGET_REMAINS_COMPARATIVE_RESEARCH_ONLY"],
        **_safety(),
    }

    return {
        "suite": "BROOKS_RESEARCH_EVIDENCE_SUITE_V1",
        "mode": mode,
        "selection_cutoff": selection_cutoff,
        "input_sessions": len(paths),
        "eligible_sessions": len(accepted),
        "accepted_sessions": [Path(p).name for p in accepted],
        "rejected_sessions": rejected,
        "setups": setup_reports,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--mode", choices=("SELECTION", "OOS"), default="SELECTION")
    parser.add_argument("--selection-cutoff")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = build_report(
        args.paths,
        mode=args.mode,
        selection_cutoff=args.selection_cutoff,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
