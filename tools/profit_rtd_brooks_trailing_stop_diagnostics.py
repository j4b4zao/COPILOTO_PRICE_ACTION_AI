"""
tools/profit_rtd_brooks_trailing_stop_diagnostics.py

Diagnostico research-only da captura Brooks de trailing stop.

Compara:
- todas as revisoes intrabar persistidas;
- ultima revisao de cada candle_id (EXACT_CANDLE_LAST_REVISION).

Objetivo:
descobrir se TRAILING_STOP_ADVANCE ocorreu intrabar e desapareceu no fechamento,
ou se o motor nunca encontrou confirmacao estrutural nas sessoes observadas.

Nao altera arquivos e nao influencia Score/Risk/Decision/Alert/execucao.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pa(sample):
    value = sample.get("price_action")
    return value if isinstance(value, dict) else {}


def _candle_id(sample):
    evidence = sample.get("candle_evidence")
    if not isinstance(evidence, dict):
        return ""
    return str(evidence.get("candle_id") or "")


def _last_revision(samples):
    by_id = {}
    order = []

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        cid = _candle_id(sample)
        if not cid:
            continue

        if cid not in by_id:
            order.append(cid)

        by_id[cid] = sample

    return [by_id[cid] for cid in order]


def _analyze(samples):
    states = Counter()
    statuses = Counter()
    reasons = Counter()

    eligible = 0
    advances = 0
    holds = 0
    structural_true = 0
    trailing_active = 0
    stop_improved = 0
    latest_swing_present = 0

    advance_candles = []
    structural_without_advance = []

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        pa = _pa(sample)
        status = str(pa.get("brooks_management_capture_status") or "")
        state = str(pa.get("brooks_management_state") or "")
        cid = _candle_id(sample)

        statuses[status] += 1
        states[state] += 1

        reason = str(pa.get("brooks_management_reason") or "")
        if reason:
            reasons[reason] += 1

        if status in {"CAPTURED", "REJECTED"}:
            eligible += 1

        if state == "TRAILING_STOP_ADVANCE":
            advances += 1
            advance_candles.append(cid)

        if state in {"TRAILING_STOP_HOLD", "PROTECTIVE_STOP_HOLD"}:
            holds += 1

        structural = bool(
            pa.get("brooks_management_structural_advance_confirmed")
        )
        if structural:
            structural_true += 1
            if state != "TRAILING_STOP_ADVANCE":
                structural_without_advance.append(cid)

        if bool(pa.get("brooks_management_trailing_active")):
            trailing_active += 1

        if bool(pa.get("brooks_management_stop_improved")):
            stop_improved += 1

        swing_price = pa.get("brooks_management_latest_swing_price")
        try:
            if float(swing_price) > 0:
                latest_swing_present += 1
        except (TypeError, ValueError):
            pass

    return {
        "samples": len(samples),
        "eligible": eligible,
        "advances": advances,
        "holds": holds,
        "structural_advance_true": structural_true,
        "trailing_active": trailing_active,
        "stop_improved": stop_improved,
        "latest_swing_present": latest_swing_present,
        "states": dict(states),
        "capture_statuses": dict(statuses),
        "reasons": dict(reasons),
        "advance_candles": advance_candles,
        "structural_without_advance": structural_without_advance,
    }


def diagnose_file(path):
    payload = _load(path)
    raw = [
        x for x in (payload.get("samples") or [])
        if isinstance(x, dict)
    ]
    exact = _last_revision(raw)

    return {
        "file": str(path),
        "raw": _analyze(raw),
        "exact_last_revision": _analyze(exact),
    }


def diagnose_many(paths):
    reports = [diagnose_file(path) for path in paths]

    raw_totals = defaultdict(int)
    exact_totals = defaultdict(int)
    raw_states = Counter()
    exact_states = Counter()
    raw_reasons = Counter()
    exact_reasons = Counter()
    raw_advance_ids = []
    exact_advance_ids = []

    numeric_keys = (
        "samples",
        "eligible",
        "advances",
        "holds",
        "structural_advance_true",
        "trailing_active",
        "stop_improved",
        "latest_swing_present",
    )

    for report in reports:
        for key in numeric_keys:
            raw_totals[key] += int(report["raw"].get(key, 0))
            exact_totals[key] += int(
                report["exact_last_revision"].get(key, 0)
            )

        raw_states.update(report["raw"].get("states") or {})
        exact_states.update(
            report["exact_last_revision"].get("states") or {}
        )
        raw_reasons.update(report["raw"].get("reasons") or {})
        exact_reasons.update(
            report["exact_last_revision"].get("reasons") or {}
        )

        raw_advance_ids.extend(
            report["raw"].get("advance_candles") or []
        )
        exact_advance_ids.extend(
            report["exact_last_revision"].get("advance_candles") or []
        )

    if raw_totals["advances"] > 0 and exact_totals["advances"] == 0:
        diagnosis = "INTRABAR_ADVANCES_DISAPPEAR_ON_LAST_REVISION"
    elif raw_totals["advances"] == 0:
        diagnosis = "NO_ADVANCE_IN_RAW_OR_EXACT_CAPTURE"
    else:
        diagnosis = "ADVANCE_PRESENT_IN_EXACT_CAPTURE"

    return {
        "status": "COMPLETED",
        "diagnosis": diagnosis,
        "deduplication": "EXACT_CANDLE_LAST_REVISION",
        "files": reports,
        "raw_totals": dict(raw_totals),
        "exact_totals": dict(exact_totals),
        "raw_state_counts": dict(raw_states),
        "exact_state_counts": dict(exact_states),
        "raw_reason_counts": dict(raw_reasons),
        "exact_reason_counts": dict(exact_reasons),
        "raw_advance_candle_ids": raw_advance_ids,
        "exact_advance_candle_ids": exact_advance_ids,
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Diagnostico exato/intrabar Brooks trailing stop."
    )
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = diagnose_many(args.paths)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    raw = report["raw_totals"]
    exact = report["exact_totals"]

    print("status=", report["status"])
    print("diagnosis=", report["diagnosis"])
    print("raw_samples=", raw.get("samples", 0))
    print("raw_eligible=", raw.get("eligible", 0))
    print("raw_advances=", raw.get("advances", 0))
    print(
        "raw_structural_advance_true=",
        raw.get("structural_advance_true", 0),
    )
    print(
        "raw_latest_swing_present=",
        raw.get("latest_swing_present", 0),
    )
    print("exact_candles=", exact.get("samples", 0))
    print("exact_eligible=", exact.get("eligible", 0))
    print("exact_advances=", exact.get("advances", 0))
    print(
        "exact_structural_advance_true=",
        exact.get("structural_advance_true", 0),
    )
    print(
        "exact_latest_swing_present=",
        exact.get("latest_swing_present", 0),
    )
    print(
        "exact_state_counts=",
        json.dumps(
            report["exact_state_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    print(
        "exact_reason_counts=",
        json.dumps(
            report["exact_reason_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
