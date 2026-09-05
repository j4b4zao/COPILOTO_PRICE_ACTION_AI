"""Auditoria observacional de BROOKS_BREAKOUT_PULLBACK_V1 em sessoes EXACT_CANDLE.

Este modulo NAO cria sinais operacionais. Ele apenas procura uma sequencia
explicitamente demonstravel nos campos ja capturados pelos JSONs RC54:

    tendencia -> breakout -> pullback/teste -> rejeicao/defesa -> retomada

Semantica importante
-------------------
O produtor SignalEntryDynamics nao possui fases PULLBACK ou REJECTION. As
fases reais capturadas por ``brooks_signal_phase`` sao SETUP_PENDING,
ENTRY_TRIGGERED, FOLLOW_THROUGH e ENTRY_STALLED.

O produtor BreakoutDynamics, por outro lado, emite BREAKOUT_TESTED quando o
candle volta ao nivel rompido e fecha preservando o lado do breakout. Por
isso, nesta auditoria de pesquisa:

- BREAKOUT_PENDING alinhado representa um breakout explicito do produtor;
- BREAKOUT_TESTED alinhado representa simultaneamente o teste/pullback do
  nivel e a defesa/rejeicao desse nivel;
- ENTRY_TRIGGERED ou FOLLOW_THROUGH alinhado, ocorrendo depois do teste,
  representa retomada explicita.

Estrutura BOS continua sendo aceita como evidencia explicita de breakout.
BREAKOUT_TESTED nunca e usado como inicio de uma nova sequencia.

Nao ha inferencia por retorno futuro e nenhum candle isolado e convertido em
setup. Quando a sequencia nao pode ser provada, o resultado permanece como
evidencia insuficiente.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from enums.trend import Trend
from research.price_action.brooks.breakout_pullback import (
    BreakoutPullbackObservation,
    BrooksBreakoutPullbackResearch,
)
from tools.profit_rtd_price_action_evidence_audit import _session_interval


_SIGNAL_PHASES_EMITTED = {
    "SETUP_PENDING",
    "ENTRY_TRIGGERED",
    "FOLLOW_THROUGH",
    "ENTRY_STALLED",
}

_BREAKOUT_PHASES_EMITTED = {
    "RANGE",
    "BREAKOUT_PENDING",
    "BREAKOUT_TESTED",
    "BREAKOUT_CONFIRMED",
    "BREAKOUT_FAILED",
}


def _rows(payload):
    if not isinstance(payload, dict) or payload.get("data_ready") is not True:
        return []
    rows = payload.get("samples")
    return rows if isinstance(rows, list) else []


def _exact_ready(row):
    evidence = row.get("candle_evidence") if isinstance(row, dict) else None
    return (
        isinstance(evidence, dict)
        and evidence.get("status") == "CANDLE_EVIDENCE_READY"
        and bool(evidence.get("candle_id"))
    )


def _last_revision_per_candle(rows):
    latest = {}
    order = []
    for row in rows:
        if not _exact_ready(row):
            continue
        candle_id = row["candle_evidence"]["candle_id"]
        if candle_id not in latest:
            order.append(candle_id)
        latest[candle_id] = row
    return [latest[candle_id] for candle_id in order]


def _text(value):
    return str(value or "").strip().upper()


def _trend(row):
    value = _text((row.get("structure") or {}).get("trend"))
    try:
        return Trend(value)
    except ValueError:
        return Trend.UNKNOWN


def _direction_for_trend(trend):
    if trend == Trend.UP:
        return "BUY"
    if trend == Trend.DOWN:
        return "SELL"
    return "NONE"


def _expected_directions(direction):
    if direction == "BUY":
        return {"BUY", "UP", "BULL", "BULLISH"}
    if direction == "SELL":
        return {"SELL", "DOWN", "BEAR", "BEARISH"}
    return set()


def _direction_aligned(value, direction):
    return _text(value) in _expected_directions(direction)


def _breakout_explicit(row, direction):
    structure = row.get("structure") or {}
    pa = row.get("price_action") or {}

    if direction == "BUY" and structure.get("bos_up") is True:
        return True, "STRUCTURE_BOS_UP"
    if direction == "SELL" and structure.get("bos_down") is True:
        return True, "STRUCTURE_BOS_DOWN"

    phase = _text(pa.get("brooks_breakout_phase"))
    if (
        phase == "BREAKOUT_PENDING"
        and _direction_aligned(pa.get("brooks_breakout_direction"), direction)
    ):
        return True, "PA_BROOKS_BREAKOUT_PENDING"

    return False, None


def _pullback_rejection_explicit(row, direction):
    """Retorna teste/pullback + defesa apenas quando o produtor os prova.

    BreakoutDynamics define BREAKOUT_TESTED assim:
    - UP: low toca/ultrapassa o nivel e close termina >= nivel;
    - DOWN: high toca/ultrapassa o nivel e close termina <= nivel.

    O mesmo candle demonstra o retorno ao nivel e sua defesa. Nao usamos
    padrao de candle generico nem retorno futuro para fabricar esse estado.
    """

    pa = row.get("price_action") or {}
    phase = _text(pa.get("brooks_breakout_phase"))
    aligned = _direction_aligned(
        pa.get("brooks_breakout_direction"),
        direction,
    )

    if phase == "BREAKOUT_TESTED" and aligned:
        return (
            True,
            "PA_BROOKS_BREAKOUT_TESTED",
            True,
            "PA_BROOKS_BREAKOUT_TEST_HELD",
        )

    return False, None, False, None


def _resumption_explicit(row, direction):
    pa = row.get("price_action") or {}
    signal_direction = pa.get("brooks_signal_direction")
    if not _direction_aligned(signal_direction, direction):
        return False, None

    signal_phase = _text(pa.get("brooks_signal_phase"))

    if pa.get("brooks_follow_through") is True and signal_phase == "FOLLOW_THROUGH":
        return True, "PA_BROOKS_SIGNAL_FOLLOW_THROUGH"

    if pa.get("brooks_entry_triggered") is True and signal_phase in {
        "ENTRY_TRIGGERED",
        "FOLLOW_THROUGH",
    }:
        return True, "PA_BROOKS_SIGNAL_ENTRY_TRIGGERED"

    return False, None


def _structure_invalidated(row, direction):
    structure = row.get("structure") or {}
    if direction == "BUY":
        return structure.get("choch") is True and _text(structure.get("trend")) == "DOWN"
    if direction == "SELL":
        return structure.get("choch") is True and _text(structure.get("trend")) == "UP"
    return False


def _producer_phase_coverage(rows):
    signal_phases = sorted({
        _text((row.get("price_action") or {}).get("brooks_signal_phase"))
        for row in rows
        if _text((row.get("price_action") or {}).get("brooks_signal_phase"))
    })
    breakout_phases = sorted({
        _text((row.get("price_action") or {}).get("brooks_breakout_phase"))
        for row in rows
        if _text((row.get("price_action") or {}).get("brooks_breakout_phase"))
    })
    return {
        "observed_signal_phases": signal_phases,
        "observed_breakout_phases": breakout_phases,
        "signal_phase_contract": sorted(_SIGNAL_PHASES_EMITTED),
        "breakout_phase_contract": sorted(_BREAKOUT_PHASES_EMITTED),
        "pullback_source": "BROOKS_BREAKOUT_PHASE_BREAKOUT_TESTED",
        "rejection_source": "BROOKS_BREAKOUT_PHASE_BREAKOUT_TESTED_HOLD",
        "resumption_source": "BROOKS_SIGNAL_ENTRY_OR_FOLLOW_THROUGH_AFTER_TEST",
    }


def audit_session(path, *, max_sequence_candles=20):
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    raw_rows = _rows(payload)

    if not raw_rows:
        return {
            "session": source.name,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["DATA_READY_SESSION_REQUIRED"],
            **_safety(),
        }
    if not all(_exact_ready(row) for row in raw_rows):
        return {
            "session": source.name,
            "status": "SESSION_NOT_ELIGIBLE",
            "reasons": ["EXACT_CANDLE_IDENTITY_REQUIRED"],
            **_safety(),
        }

    rows = _last_revision_per_candle(raw_rows)
    classifier = BrooksBreakoutPullbackResearch()
    sequences = []
    incomplete = []

    for index, breakout_row in enumerate(rows):
        trend = _trend(breakout_row)
        direction = _direction_for_trend(trend)
        if direction == "NONE":
            continue

        breakout_detected, breakout_source = _breakout_explicit(
            breakout_row,
            direction,
        )
        if not breakout_detected:
            continue

        evidence = {
            "breakout": {
                "candle_id": breakout_row["candle_evidence"]["candle_id"],
                "source": breakout_source,
            }
        }
        pullback = False
        rejection = False
        resumption = False
        invalidated = False

        end = min(len(rows), index + 1 + int(max_sequence_candles))
        for row in rows[index + 1:end]:
            if _structure_invalidated(row, direction):
                invalidated = True
                evidence["invalidation"] = {
                    "candle_id": row["candle_evidence"]["candle_id"],
                    "source": "OPPOSITE_CHOCH",
                }
                break

            if not pullback:
                (
                    pullback,
                    pullback_source,
                    rejection,
                    rejection_source,
                ) = _pullback_rejection_explicit(row, direction)

                if pullback:
                    candle_id = row["candle_evidence"]["candle_id"]
                    evidence["pullback"] = {
                        "candle_id": candle_id,
                        "source": pullback_source,
                    }
                    evidence["rejection"] = {
                        "candle_id": candle_id,
                        "source": rejection_source,
                    }
                continue

            if not resumption:
                resumption, source_name = _resumption_explicit(row, direction)
                if resumption:
                    evidence["resumption"] = {
                        "candle_id": row["candle_evidence"]["candle_id"],
                        "source": source_name,
                    }
                    break

        observation = BreakoutPullbackObservation(
            trend=trend,
            breakout_direction=direction,
            breakout_detected=breakout_detected,
            pullback_detected=pullback,
            rejection_detected=rejection,
            resumption_detected=resumption,
            structural_level_lost=invalidated,
            candle_id=breakout_row["candle_evidence"]["candle_id"],
        )
        result = classifier.evaluate(observation)
        item = {
            "direction": direction,
            "matched": result.matched,
            "invalidated": result.invalidated,
            "sequence_complete": result.sequence_complete,
            "reasons": list(result.reasons),
            "evidence": evidence,
        }
        if result.matched:
            sequences.append(item)
        else:
            incomplete.append(item)

    status = (
        "MATCHES_OBSERVED"
        if sequences
        else "INSUFFICIENT_SEQUENCE_EVIDENCE"
    )
    reasons = (
        []
        if sequences
        else ["NO_COMPLETE_EXPLICIT_BREAKOUT_PULLBACK_SEQUENCE"]
    )
    return {
        "session": source.name,
        "status": status,
        "exact_candles": len(rows),
        "complete_sequences": len(sequences),
        "incomplete_candidates": len(incomplete),
        "sequences": sequences,
        "incomplete": incomplete,
        "producer_phase_coverage": _producer_phase_coverage(rows),
        "reasons": reasons,
        **_safety(),
    }


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


def audit(paths, *, max_sequence_candles=20):
    candidates = []
    for raw_path in paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates.append((path, _session_interval(_rows(payload))))
    candidates.sort(key=lambda item: (
        item[1] is None,
        item[1][0] if item[1] is not None else float("inf"),
        item[0].name,
    ))

    sessions = []
    accepted_intervals = []
    for path, interval in candidates:
        overlap = next((
            prior_name
            for prior_name, prior_interval in accepted_intervals
            if interval is not None
            and interval[0] <= prior_interval[1]
            and prior_interval[0] <= interval[1]
        ), None)
        if overlap is not None:
            sessions.append({
                "session": path.name,
                "status": "SESSION_NOT_ELIGIBLE",
                "reasons": ["TEMPORAL_OVERLAP"],
                "overlaps_with": overlap,
                **_safety(),
            })
            continue

        result = audit_session(
            path,
            max_sequence_candles=max_sequence_candles,
        )
        sessions.append(result)
        if (
            interval is not None
            and result.get("status") in {
                "MATCHES_OBSERVED",
                "INSUFFICIENT_SEQUENCE_EVIDENCE",
            }
        ):
            accepted_intervals.append((path.name, interval))

    complete = sum(
        item.get("complete_sequences", 0)
        for item in sessions
    )
    eligible_sessions = sum(
        item.get("status") in {
            "MATCHES_OBSERVED",
            "INSUFFICIENT_SEQUENCE_EVIDENCE",
        }
        for item in sessions
    )
    return {
        "status": (
            "MATCHES_OBSERVED"
            if complete
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "eligible_sessions": eligible_sessions,
        "sessions": sessions,
        "complete_sequences": complete,
        "hypothesis_freeze_allowed": False,
        "reasons": (
            ["COMPLETE_EXPLICIT_SEQUENCE_OBSERVED_RESEARCH_ONLY"]
            if complete
            else ["NO_COMPLETE_EXPLICIT_BREAKOUT_PULLBACK_SEQUENCE"]
        ),
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--max-sequence-candles", type=int, default=20)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    result = audit(
        args.paths,
        max_sequence_candles=args.max_sequence_candles,
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
