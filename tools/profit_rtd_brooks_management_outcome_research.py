"""
tools/profit_rtd_brooks_management_outcome_research.py

Stage 3 — Brooks Lifecycle Outcome Research.

Pesquisa offline e observacional sobre episodios gerados pela Stage 2.

Objetivos:
- medir MFE e MAE em R a partir da entrada;
- verificar se o stop inicial teria sido tocado;
- verificar se o trailing hipotetico teria sido tocado;
- registrar o candle de saida hipotetica;
- registrar R protegido no momento da saida;
- comparar baseline (initial stop) vs trailing stop.

Nao:
- altera RiskManager;
- altera Score;
- altera Decision;
- altera Alert;
- envia ordens;
- promove hipotese;
- declara performance validada.

Hipotese de execucao conservadora:
- para BUY, stop e tocado quando candle.low <= stop;
- para SELL, stop e tocado quando candle.high >= stop;
- o trailing aplicado em um candle passa a valer somente a partir do candle
  seguinte, evitando look-ahead intrabar.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SETUP_NAME = "BROOKS_MANAGEMENT_OUTCOME_RESEARCH_V1"
EPS = 1e-9


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
        "dynamic_management_validated": False,
    }


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _session_exact_samples(session_source_payload):
    samples = session_source_payload.get("samples") or []
    latest = {}
    order = []

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        evidence = sample.get("candle_evidence")
        if not isinstance(evidence, dict):
            continue

        cid = str(evidence.get("candle_id") or "")
        if not cid:
            continue

        if cid not in latest:
            order.append(cid)

        latest[cid] = sample

    return [latest[cid] for cid in order]


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _index_exact_samples(samples):
    by_id = {}
    for index, sample in enumerate(samples):
        evidence = sample.get("candle_evidence") or {}
        cid = str(evidence.get("candle_id") or "")
        if cid:
            by_id[cid] = (index, sample)
    return by_id


def _candle_values(sample):
    evidence = sample.get("candle_evidence") or {}
    return {
        "high": _f(evidence.get("high")),
        "low": _f(evidence.get("low")),
        "close": _f(evidence.get("close")),
        "candle_id": str(evidence.get("candle_id") or ""),
    }


def _risk_size(direction, entry, stop):
    if direction == "BUY":
        return entry - stop
    if direction == "SELL":
        return stop - entry
    return 0.0


def _mfe_mae(direction, entry, high, low, risk):
    if risk <= EPS:
        return 0.0, 0.0

    if direction == "BUY":
        mfe_r = max(0.0, (high - entry) / risk)
        mae_r = max(0.0, (entry - low) / risk)
    else:
        mfe_r = max(0.0, (entry - low) / risk)
        mae_r = max(0.0, (high - entry) / risk)

    return mfe_r, mae_r


def _stop_touched(direction, candle, stop):
    if direction == "BUY":
        return candle["low"] <= stop + EPS
    if direction == "SELL":
        return candle["high"] >= stop - EPS
    return False


def _protected_r(direction, entry, initial_stop, current_stop):
    risk = _risk_size(direction, entry, initial_stop)
    if risk <= EPS:
        return 0.0

    if direction == "BUY":
        return (current_stop - entry) / risk

    return (entry - current_stop) / risk


def analyze_episode(episode, exact_samples, exact_index):
    direction = str(episode.get("direction") or "").upper()
    entry = _f(episode.get("entry_price"))
    initial_stop = _f(episode.get("initial_stop"))
    entry_candle_id = str(
        episode.get("entry_event_candle_id") or ""
    )

    entry_pair = exact_index.get(entry_candle_id)
    if entry_pair is None:
        return {
            "episode_id": episode.get("episode_id"),
            "status": "ENTRY_CANDLE_NOT_FOUND",
            "eligible": False,
        }

    entry_idx = entry_pair[0]
    risk = _risk_size(direction, entry, initial_stop)

    if direction not in {"BUY", "SELL"} or risk <= EPS:
        return {
            "episode_id": episode.get("episode_id"),
            "status": "INVALID_ENTRY_GEOMETRY",
            "eligible": False,
        }

    observations = {
        int(obs.get("observation_exact_index")): obs
        for obs in (episode.get("observations") or [])
        if isinstance(obs, dict)
        and obs.get("observation_exact_index") is not None
    }

    max_mfe_r = 0.0
    max_mae_r = 0.0

    baseline_stop_hit = False
    baseline_exit_candle_id = None
    baseline_exit_index = None

    trailing_stop_hit = False
    trailing_exit_candle_id = None
    trailing_exit_index = None
    trailing_exit_stop = None
    trailing_exit_protected_r = None

    active_trailing_stop = initial_stop

    # Comeca no candle seguinte ao candle de entrada.
    for idx in range(entry_idx + 1, len(exact_samples)):
        candle = _candle_values(exact_samples[idx])

        mfe_r, mae_r = _mfe_mae(
            direction,
            entry,
            candle["high"],
            candle["low"],
            risk,
        )
        max_mfe_r = max(max_mfe_r, mfe_r)
        max_mae_r = max(max_mae_r, mae_r)

        if not baseline_stop_hit and _stop_touched(
            direction,
            candle,
            initial_stop,
        ):
            baseline_stop_hit = True
            baseline_exit_candle_id = candle["candle_id"]
            baseline_exit_index = idx

        # O stop ativo deve ser o stop que veio do candle anterior.
        if not trailing_stop_hit and _stop_touched(
            direction,
            candle,
            active_trailing_stop,
        ):
            trailing_stop_hit = True
            trailing_exit_candle_id = candle["candle_id"]
            trailing_exit_index = idx
            trailing_exit_stop = active_trailing_stop
            trailing_exit_protected_r = _protected_r(
                direction,
                entry,
                initial_stop,
                active_trailing_stop,
            )

        # Mesmo se o stop foi tocado neste candle, nao aplicamos nova revisao
        # depois da saida hipotetica.
        if trailing_stop_hit:
            break

        # Revisao produzida neste candle vale somente no proximo.
        obs = observations.get(idx)
        if obs and bool(obs.get("revision_applied")):
            candidate = _f(
                obs.get("current_stop_after"),
                active_trailing_stop,
            )

            if direction == "BUY" and candidate > active_trailing_stop:
                active_trailing_stop = candidate
            elif direction == "SELL" and candidate < active_trailing_stop:
                active_trailing_stop = candidate

    return {
        "episode_id": episode.get("episode_id"),
        "entry_event_candle_id": entry_candle_id,
        "direction": direction,
        "entry_price": entry,
        "initial_stop": initial_stop,
        "initial_risk_points": risk,
        "status": "OUTCOME_RESEARCH_COMPLETED",
        "eligible": True,
        "mfe_r": max_mfe_r,
        "mae_r": max_mae_r,
        "baseline_initial_stop_hit": baseline_stop_hit,
        "baseline_exit_candle_id": baseline_exit_candle_id,
        "baseline_exit_exact_index": baseline_exit_index,
        "trailing_stop_hit": trailing_stop_hit,
        "trailing_exit_candle_id": trailing_exit_candle_id,
        "trailing_exit_exact_index": trailing_exit_index,
        "trailing_exit_stop": trailing_exit_stop,
        "trailing_exit_protected_r": trailing_exit_protected_r,
        "final_active_trailing_stop": active_trailing_stop,
        "final_protected_r": _protected_r(
            direction,
            entry,
            initial_stop,
            active_trailing_stop,
        ),
        "stop_revision_count": int(
            episode.get("stop_revision_count") or 0
        ),
    }


def analyze_session(lifecycle_session, source_payload):
    exact_samples = _session_exact_samples(source_payload)
    exact_index = _index_exact_samples(exact_samples)

    episode_reports = [
        analyze_episode(episode, exact_samples, exact_index)
        for episode in (lifecycle_session.get("episodes") or [])
        if isinstance(episode, dict)
    ]

    eligible = [x for x in episode_reports if x.get("eligible")]

    baseline_hits = sum(
        1 for x in eligible
        if x["baseline_initial_stop_hit"]
    )
    trailing_hits = sum(
        1 for x in eligible
        if x["trailing_stop_hit"]
    )
    protected_positive = sum(
        1 for x in eligible
        if (
            x["trailing_exit_protected_r"] is not None
            and x["trailing_exit_protected_r"] > 0
        )
    )
    protected_breakeven_or_better = sum(
        1 for x in eligible
        if (
            x["trailing_exit_protected_r"] is not None
            and x["trailing_exit_protected_r"] >= 0
        )
    )

    return {
        "status": (
            "OUTCOME_RESEARCH_COMPLETED"
            if eligible
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "source": lifecycle_session.get("source"),
        "exact_candles": len(exact_samples),
        "eligible_episodes": len(eligible),
        "baseline_initial_stop_hits": baseline_hits,
        "trailing_stop_hits": trailing_hits,
        "trailing_positive_r_exits": protected_positive,
        "trailing_breakeven_or_better_exits": (
            protected_breakeven_or_better
        ),
        "episodes": episode_reports,
        **_safety(),
    }


def analyze_many(lifecycle_payload):
    sessions = lifecycle_payload.get("sessions") or []
    reports = []

    for lifecycle_session in sessions:
        source = lifecycle_session.get("source")
        if not source:
            reports.append({
                "status": "SOURCE_NOT_FOUND",
                "source": source,
                "eligible_episodes": 0,
                "episodes": [],
                **_safety(),
            })
            continue

        source_payload = _load_json(source)
        reports.append(
            analyze_session(lifecycle_session, source_payload)
        )

    eligible_episodes = sum(
        x.get("eligible_episodes", 0) for x in reports
    )
    baseline_hits = sum(
        x.get("baseline_initial_stop_hits", 0)
        for x in reports
    )
    trailing_hits = sum(
        x.get("trailing_stop_hits", 0)
        for x in reports
    )
    positive_exits = sum(
        x.get("trailing_positive_r_exits", 0)
        for x in reports
    )
    be_or_better = sum(
        x.get("trailing_breakeven_or_better_exits", 0)
        for x in reports
    )

    return {
        "setup": SETUP_NAME,
        "status": (
            "MULTI_SESSION_OUTCOME_RESEARCH_COMPLETED"
            if eligible_episodes
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "accepted_session_count": len(reports),
        "eligible_episodes": eligible_episodes,
        "baseline_initial_stop_hits": baseline_hits,
        "trailing_stop_hits": trailing_hits,
        "trailing_positive_r_exits": positive_exits,
        "trailing_breakeven_or_better_exits": be_or_better,
        "performance_validated": False,
        "validation_reason": (
            "DESCRIPTIVE_OUTCOME_RESEARCH_ONLY_NO_PERFORMANCE_CLAIM"
        ),
        "sessions": reports,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Brooks lifecycle outcome research."
    )
    parser.add_argument("lifecycle_report")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    lifecycle_payload = _load_json(args.lifecycle_report)
    report = analyze_many(lifecycle_payload)

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
    print("eligible_episodes=", report["eligible_episodes"])
    print(
        "baseline_initial_stop_hits=",
        report["baseline_initial_stop_hits"],
    )
    print(
        "trailing_stop_hits=",
        report["trailing_stop_hits"],
    )
    print(
        "trailing_positive_r_exits=",
        report["trailing_positive_r_exits"],
    )
    print(
        "trailing_breakeven_or_better_exits=",
        report["trailing_breakeven_or_better_exits"],
    )
    print("performance_validated=", report["performance_validated"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
