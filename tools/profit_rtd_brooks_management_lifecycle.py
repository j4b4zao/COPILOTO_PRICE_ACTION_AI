"""
tools/profit_rtd_brooks_management_lifecycle.py

Stage 2 — Brooks Dynamic Management / Trade Lifecycle Research.

Research-only e observacional.

Este modulo:
- trabalha somente sobre sessoes Brooks ja persistidas;
- deduplica por candle_id usando EXACT_CANDLE_LAST_REVISION;
- cria um episodio para cada entrada Brooks elegivel;
- acompanha a mesma entrada atraves dos candles exatos seguintes;
- persiste um current_stop hipotetico por episodio;
- usa ProtectiveTrailingStopDynamics sem alterar seu algoritmo;
- nao calcula performance, PnL, partials ou outcomes;
- nao influencia Score, Risk, Decision, Alert ou execucao.

Importante:
A engine Ch.29 ignora o ultimo candle recebido por considerar que ele pode estar
em formacao. Como este reprocessamento trabalha com candles exatos/fechados,
cada avaliacao adiciona um "sentinel" sintetico no fim do historico. A engine
descarta somente esse sentinel e passa a enxergar todos os candles fechados
ate o candle de observacao.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import SimpleNamespace

from analysis.price_action.protective_trailing_stop_dynamics import (
    ProtectiveTrailingStopDynamics,
)


SETUP_NAME = "BROOKS_MANAGEMENT_LIFECYCLE_V1"
DEDUPLICATION = "EXACT_CANDLE_LAST_REVISION"
_ENGINE = ProtectiveTrailingStopDynamics()


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
        "performance_claim_allowed": False,
        "hypothesis_freeze_allowed": False,
    }


def _price_action(sample):
    value = sample.get("price_action")
    return value if isinstance(value, dict) else {}


def _evidence(sample):
    value = sample.get("candle_evidence")
    return value if isinstance(value, dict) else {}


def _candle_id(sample):
    return str(_evidence(sample).get("candle_id") or "")


def _deduplicate(samples):
    latest = {}
    order = []

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        candle_id = _candle_id(sample)
        if not candle_id:
            continue

        if candle_id not in latest:
            order.append(candle_id)

        latest[candle_id] = sample

    return [latest[candle_id] for candle_id in order]


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normalize_direction(value):
    direction = str(value or "").upper().strip()

    if direction == "UP":
        return "BUY"
    if direction == "DOWN":
        return "SELL"
    if direction in {"BUY", "SELL"}:
        return direction

    return "NONE"


def _to_candle(sample):
    evidence = _evidence(sample)

    return SimpleNamespace(
        open=_float(evidence.get("open")),
        high=_float(evidence.get("high")),
        low=_float(evidence.get("low")),
        close=_float(evidence.get("close")),
        candle_id=str(evidence.get("candle_id") or ""),
    )


def _synthetic_sentinel(last_candle):
    return SimpleNamespace(
        open=last_candle.close,
        high=last_candle.close,
        low=last_candle.close,
        close=last_candle.close,
        candle_id=f"{last_candle.candle_id}|SENTINEL",
    )


def _result_dict(result):
    if is_dataclass(result):
        return asdict(result)

    if hasattr(result, "__dict__"):
        return dict(vars(result))

    raise TypeError(
        "ProtectiveTrailingStopDynamics result is not serializable"
    )


def _entry_from_sample(sample, exact_index):
    pa = _price_action(sample)

    triggered = bool(
        pa.get(
            "brooks_stop_target_entry_triggered",
            pa.get("brooks_entry_triggered", False),
        )
    )

    direction = _normalize_direction(
        pa.get(
            "brooks_stop_target_direction",
            pa.get("brooks_signal_direction"),
        )
    )

    entry_price = _float(
        pa.get("brooks_stop_target_entry_price")
    )
    initial_stop = _float(
        pa.get("brooks_stop_target_initial_stop")
    )

    stop_geometry_valid = bool(
        pa.get("brooks_stop_target_stop_geometry_valid")
    )

    candle_id = _candle_id(sample)

    if not triggered:
        return None

    if direction not in {"BUY", "SELL"}:
        return None

    if not stop_geometry_valid:
        return None

    if entry_price <= 0 or initial_stop <= 0:
        return None

    if direction == "BUY" and initial_stop >= entry_price:
        return None

    if direction == "SELL" and initial_stop <= entry_price:
        return None

    return {
        "episode_id": f"{candle_id}|{direction}",
        "entry_event_candle_id": candle_id,
        "entry_exact_index": int(exact_index),
        "direction": direction,
        "entry_price": entry_price,
        "initial_stop": initial_stop,
        "current_stop": initial_stop,
        "stop_revision_count": 0,
        "observations": [],
    }


def _apply_observation(
    episode,
    closed_history,
    observation_sample,
    observation_index,
):
    current = _to_candle(observation_sample)

    engine_history = list(closed_history)
    engine_history.append(_synthetic_sentinel(current))

    before = float(episode["current_stop"])

    result = _ENGINE.analyze(
        engine_history,
        direction=episode["direction"],
        entry_price=episode["entry_price"],
        initial_stop=episode["initial_stop"],
        current_stop=before,
        tick_size=1.0,
    )
    data = _result_dict(result)

    proposed = _float(data.get("proposed_stop"), before)
    state = str(data.get("state") or "")

    after = before
    revision_applied = False

    if state == "TRAILING_STOP_ADVANCE":
        if episode["direction"] == "BUY" and proposed > before:
            after = proposed
            revision_applied = True
        elif episode["direction"] == "SELL" and proposed < before:
            after = proposed
            revision_applied = True

    if revision_applied:
        episode["stop_revision_count"] += 1
        episode["current_stop"] = after

    observation = {
        "observation_candle_id": _candle_id(observation_sample),
        "observation_exact_index": int(observation_index),
        "state": state,
        "reason": str(data.get("reason") or ""),
        "previous_stop": before,
        "proposed_stop": proposed,
        "current_stop_after": after,
        "revision_applied": revision_applied,
        "trailing_active": bool(data.get("trailing_active")),
        "stop_improved": bool(data.get("stop_improved")),
        "stop_loosened": bool(data.get("stop_loosened")),
        "structural_advance_confirmed": bool(
            data.get("structural_advance_confirmed")
        ),
        "latest_swing_index": data.get("latest_swing_index"),
        "latest_swing_price": _float(
            data.get("latest_swing_price")
        ),
        "protected_r": _float(data.get("protected_r")),
    }

    episode["observations"].append(observation)


def build_lifecycles(payload):
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")

    raw_samples = payload.get("samples") or []
    exact_samples = _deduplicate(raw_samples)
    exact_candles = [_to_candle(sample) for sample in exact_samples]

    episodes = []

    for entry_index, sample in enumerate(exact_samples):
        episode = _entry_from_sample(sample, entry_index)
        if episode is None:
            continue

        # O proprio candle de entrada nao e usado para mover o stop.
        # A primeira observacao ocorre no candle exato seguinte.
        for observation_index in range(
            entry_index + 1,
            len(exact_samples),
        ):
            # Todos os candles fechados ate e incluindo o candle
            # de observacao sao fornecidos a engine; um sentinel extra
            # e descartado internamente pela engine.
            closed_history = exact_candles[: observation_index + 1]

            _apply_observation(
                episode,
                closed_history,
                exact_samples[observation_index],
                observation_index,
            )

        episodes.append(episode)

    advance_observations = sum(
        1
        for episode in episodes
        for observation in episode["observations"]
        if observation["revision_applied"]
    )

    episodes_with_advance = sum(
        1
        for episode in episodes
        if episode["stop_revision_count"] > 0
    )

    report = {
        "setup": SETUP_NAME,
        "status": (
            "LIFECYCLE_RESEARCH_COMPLETED"
            if episodes
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "deduplication": DEDUPLICATION,
        "raw_samples": len(raw_samples),
        "exact_candles": len(exact_samples),
        "eligible_entry_episodes": len(episodes),
        "episodes_with_stop_advance": episodes_with_advance,
        "stop_advance_observations": advance_observations,
        "dynamic_management_validated": False,
        "validation_reason": (
            "RESEARCH_ONLY_LIFECYCLE_NO_PERFORMANCE_CLAIM"
        ),
        "episodes": episodes,
        **_safety(),
    }

    return report


def build_many(paths):
    sessions = []

    for path in paths:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8")
        )
        report = build_lifecycles(payload)
        report["source"] = str(path)
        sessions.append(report)

    total_exact = sum(x["exact_candles"] for x in sessions)
    total_episodes = sum(
        x["eligible_entry_episodes"] for x in sessions
    )
    total_with_advance = sum(
        x["episodes_with_stop_advance"] for x in sessions
    )
    total_advances = sum(
        x["stop_advance_observations"] for x in sessions
    )

    return {
        "setup": SETUP_NAME,
        "status": (
            "MULTI_SESSION_LIFECYCLE_RESEARCH_COMPLETED"
            if total_episodes
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "accepted_session_count": len(sessions),
        "exact_candles": total_exact,
        "eligible_entry_episodes": total_episodes,
        "episodes_with_stop_advance": total_with_advance,
        "stop_advance_observations": total_advances,
        "dynamic_management_validated": False,
        "validation_reason": (
            "RESEARCH_ONLY_LIFECYCLE_NO_PERFORMANCE_CLAIM"
        ),
        "sessions": sessions,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Brooks management lifecycle research."
    )
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = build_many(args.paths)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("status=", report["status"])
    print(
        "accepted_session_count=",
        report["accepted_session_count"],
    )
    print("exact_candles=", report["exact_candles"])
    print(
        "eligible_entry_episodes=",
        report["eligible_entry_episodes"],
    )
    print(
        "episodes_with_stop_advance=",
        report["episodes_with_stop_advance"],
    )
    print(
        "stop_advance_observations=",
        report["stop_advance_observations"],
    )
    print(
        "dynamic_management_validated=",
        report["dynamic_management_validated"],
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
