"""
tools/profit_rtd_brooks_management_exit_bounded_outcome.py

Stage 3.2 — Brooks Exit-Bounded Outcome Research.

Corrige a principal limitacao metodologica da Stage 3/3.1:
MFE/MAE passam a ser medidos somente ate a saida hipotetica de cada modelo.

Dois caminhos sao avaliados separadamente:
1. baseline: mantem apenas o initial_stop;
2. trailing: usa o stop dinamico hipotetico do lifecycle.

Regras conservadoras:
- a avaliacao comeca no candle seguinte ao candle de entrada;
- stop tocado no candle encerra aquele caminho;
- revisao trailing produzida no candle N so vale a partir do candle N+1;
- nao ha inferencia intrabar alem do toque do stop;
- episodio sem stop ate o fim da amostra fica censurado (SESSION_END_CENSORED).

Nao ha PnL monetario, custos, slippage, edge ou promocao de regra.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

SETUP_NAME = "BROOKS_MANAGEMENT_EXIT_BOUNDED_OUTCOME_V1"
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
        "performance_validated": False,
    }


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _mean(values):
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def _median(values):
    values = list(values)
    return statistics.median(values) if values else 0.0


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dedupe_exact(payload):
    latest = {}
    order = []

    for sample in payload.get("samples") or []:
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


def _candle(sample):
    e = sample.get("candle_evidence") or {}
    return {
        "candle_id": str(e.get("candle_id") or ""),
        "high": _f(e.get("high")),
        "low": _f(e.get("low")),
        "close": _f(e.get("close")),
    }


def _risk(direction, entry, initial_stop):
    if direction == "BUY":
        return entry - initial_stop
    if direction == "SELL":
        return initial_stop - entry
    return 0.0


def _stop_hit(direction, candle, stop):
    if direction == "BUY":
        return candle["low"] <= stop + EPS
    if direction == "SELL":
        return candle["high"] >= stop - EPS
    return False


def _excursion(direction, entry, candle, risk):
    if direction == "BUY":
        favorable = max(0.0, (candle["high"] - entry) / risk)
        adverse = max(0.0, (entry - candle["low"]) / risk)
    else:
        favorable = max(0.0, (entry - candle["low"]) / risk)
        adverse = max(0.0, (candle["high"] - entry) / risk)
    return favorable, adverse


def _stop_r(direction, entry, initial_stop, stop):
    risk = _risk(direction, entry, initial_stop)
    if risk <= EPS:
        return 0.0
    if direction == "BUY":
        return (stop - entry) / risk
    return (entry - stop) / risk


def _close_r(direction, entry, initial_stop, close):
    risk = _risk(direction, entry, initial_stop)
    if risk <= EPS:
        return 0.0
    if direction == "BUY":
        return (close - entry) / risk
    return (entry - close) / risk


def analyze_episode(episode, exact_samples):
    direction = str(episode.get("direction") or "").upper()
    entry = _f(episode.get("entry_price"))
    initial_stop = _f(episode.get("initial_stop"))
    entry_cid = str(episode.get("entry_event_candle_id") or "")

    index_by_id = {
        _candle(sample)["candle_id"]: idx
        for idx, sample in enumerate(exact_samples)
        if _candle(sample)["candle_id"]
    }

    if entry_cid not in index_by_id:
        return {
            "episode_id": episode.get("episode_id"),
            "eligible": False,
            "status": "ENTRY_CANDLE_NOT_FOUND",
        }

    risk = _risk(direction, entry, initial_stop)
    if direction not in {"BUY", "SELL"} or risk <= EPS:
        return {
            "episode_id": episode.get("episode_id"),
            "eligible": False,
            "status": "INVALID_ENTRY_GEOMETRY",
        }

    entry_idx = index_by_id[entry_cid]
    observations = {
        int(obs["observation_exact_index"]): obs
        for obs in (episode.get("observations") or [])
        if isinstance(obs, dict)
        and obs.get("observation_exact_index") is not None
    }

    baseline = {
        "active": True,
        "exit_type": None,
        "exit_candle_id": None,
        "exit_exact_index": None,
        "exit_r": None,
        "mfe_r": 0.0,
        "mae_r": 0.0,
    }
    trailing = {
        "active": True,
        "exit_type": None,
        "exit_candle_id": None,
        "exit_exact_index": None,
        "exit_r": None,
        "exit_stop": None,
        "mfe_r": 0.0,
        "mae_r": 0.0,
    }

    active_trailing_stop = initial_stop
    last_candle = None

    for idx in range(entry_idx + 1, len(exact_samples)):
        candle = _candle(exact_samples[idx])
        last_candle = candle

        favorable, adverse = _excursion(
            direction, entry, candle, risk
        )

        if baseline["active"]:
            baseline["mfe_r"] = max(
                baseline["mfe_r"], favorable
            )
            baseline["mae_r"] = max(
                baseline["mae_r"], adverse
            )

            if _stop_hit(direction, candle, initial_stop):
                baseline["active"] = False
                baseline["exit_type"] = "INITIAL_STOP"
                baseline["exit_candle_id"] = candle["candle_id"]
                baseline["exit_exact_index"] = idx
                baseline["exit_r"] = -1.0

        if trailing["active"]:
            trailing["mfe_r"] = max(
                trailing["mfe_r"], favorable
            )
            trailing["mae_r"] = max(
                trailing["mae_r"], adverse
            )

            if _stop_hit(
                direction, candle, active_trailing_stop
            ):
                trailing["active"] = False
                trailing["exit_type"] = "TRAILING_STOP"
                trailing["exit_candle_id"] = candle["candle_id"]
                trailing["exit_exact_index"] = idx
                trailing["exit_stop"] = active_trailing_stop
                trailing["exit_r"] = _stop_r(
                    direction,
                    entry,
                    initial_stop,
                    active_trailing_stop,
                )

        # Se trailing saiu neste candle, nenhuma revisao deste candle
        # pode ser aplicada depois da saida.
        if trailing["active"]:
            obs = observations.get(idx)
            if obs and bool(obs.get("revision_applied")):
                candidate = _f(
                    obs.get("current_stop_after"),
                    active_trailing_stop,
                )
                if (
                    direction == "BUY"
                    and candidate > active_trailing_stop + EPS
                ):
                    active_trailing_stop = candidate
                elif (
                    direction == "SELL"
                    and candidate < active_trailing_stop - EPS
                ):
                    active_trailing_stop = candidate

        if not baseline["active"] and not trailing["active"]:
            break

    # Episodios ainda vivos no final sao censurados. O close final e
    # registrado apenas como mark-to-market descritivo, nao como trade exit.
    if last_candle is not None:
        if baseline["active"]:
            baseline["exit_type"] = "SESSION_END_CENSORED"
            baseline["exit_candle_id"] = last_candle["candle_id"]
            baseline["exit_exact_index"] = len(exact_samples) - 1
            baseline["session_end_mark_r"] = _close_r(
                direction,
                entry,
                initial_stop,
                last_candle["close"],
            )
        if trailing["active"]:
            trailing["exit_type"] = "SESSION_END_CENSORED"
            trailing["exit_candle_id"] = last_candle["candle_id"]
            trailing["exit_exact_index"] = len(exact_samples) - 1
            trailing["session_end_mark_r"] = _close_r(
                direction,
                entry,
                initial_stop,
                last_candle["close"],
            )

    baseline["active_at_end"] = baseline["active"]
    trailing["active_at_end"] = trailing["active"]
    baseline.pop("active")
    trailing.pop("active")

    return {
        "episode_id": episode.get("episode_id"),
        "entry_event_candle_id": entry_cid,
        "direction": direction,
        "entry_price": entry,
        "initial_stop": initial_stop,
        "initial_risk_points": risk,
        "eligible": True,
        "status": "EXIT_BOUNDED_OUTCOME_COMPLETED",
        "baseline": baseline,
        "trailing": trailing,
        "final_hypothetical_trailing_stop": active_trailing_stop,
    }


def analyze_session(lifecycle_session):
    source = lifecycle_session.get("source")
    if not source:
        return {
            "status": "SOURCE_NOT_FOUND",
            "source": source,
            "eligible_episodes": 0,
            "episodes": [],
            **_safety(),
        }

    exact_samples = _dedupe_exact(_load(source))

    episodes = [
        analyze_episode(ep, exact_samples)
        for ep in (lifecycle_session.get("episodes") or [])
        if isinstance(ep, dict)
    ]
    eligible = [ep for ep in episodes if ep.get("eligible")]

    return {
        "status": (
            "EXIT_BOUNDED_SESSION_COMPLETED"
            if eligible else "MORE_EVIDENCE_REQUIRED"
        ),
        "source": source,
        "exact_candles": len(exact_samples),
        "eligible_episodes": len(eligible),
        "episodes": episodes,
        **_safety(),
    }


def analyze_many(lifecycle_payload):
    session_reports = [
        analyze_session(session)
        for session in (lifecycle_payload.get("sessions") or [])
        if isinstance(session, dict)
    ]

    episodes = [
        ep
        for session in session_reports
        for ep in session.get("episodes") or []
        if ep.get("eligible")
    ]

    baseline_stop = sum(
        ep["baseline"]["exit_type"] == "INITIAL_STOP"
        for ep in episodes
    )
    trailing_stop = sum(
        ep["trailing"]["exit_type"] == "TRAILING_STOP"
        for ep in episodes
    )
    baseline_censored = sum(
        ep["baseline"]["exit_type"] == "SESSION_END_CENSORED"
        for ep in episodes
    )
    trailing_censored = sum(
        ep["trailing"]["exit_type"] == "SESSION_END_CENSORED"
        for ep in episodes
    )

    baseline_mfe = [ep["baseline"]["mfe_r"] for ep in episodes]
    baseline_mae = [ep["baseline"]["mae_r"] for ep in episodes]
    trailing_mfe = [ep["trailing"]["mfe_r"] for ep in episodes]
    trailing_mae = [ep["trailing"]["mae_r"] for ep in episodes]

    trailing_exit_rs = [
        ep["trailing"]["exit_r"]
        for ep in episodes
        if ep["trailing"]["exit_r"] is not None
    ]

    return {
        "setup": SETUP_NAME,
        "status": (
            "MULTI_SESSION_EXIT_BOUNDED_OUTCOME_COMPLETED"
            if episodes else "MORE_EVIDENCE_REQUIRED"
        ),
        "accepted_session_count": len(session_reports),
        "eligible_episodes": len(episodes),
        "baseline_stop_exits": baseline_stop,
        "baseline_censored": baseline_censored,
        "trailing_stop_exits": trailing_stop,
        "trailing_censored": trailing_censored,
        "baseline_mfe_r_mean": _mean(baseline_mfe),
        "baseline_mfe_r_median": _median(baseline_mfe),
        "baseline_mae_r_mean": _mean(baseline_mae),
        "baseline_mae_r_median": _median(baseline_mae),
        "trailing_mfe_r_mean": _mean(trailing_mfe),
        "trailing_mfe_r_median": _median(trailing_mfe),
        "trailing_mae_r_mean": _mean(trailing_mae),
        "trailing_mae_r_median": _median(trailing_mae),
        "trailing_stop_exit_r_mean": _mean(trailing_exit_rs),
        "trailing_stop_exit_r_median": _median(trailing_exit_rs),
        "performance_validated": False,
        "validation_reason": (
            "EXIT_BOUNDED_DESCRIPTIVE_RESEARCH_ONLY_"
            "CENSORED_EPISODES_NOT_REALIZED_PERFORMANCE"
        ),
        "sessions": session_reports,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Brooks exit-bounded outcome research."
    )
    parser.add_argument("lifecycle_report")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    payload = _load(args.lifecycle_report)
    report = analyze_many(payload)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    keys = [
        "status",
        "accepted_session_count",
        "eligible_episodes",
        "baseline_stop_exits",
        "baseline_censored",
        "trailing_stop_exits",
        "trailing_censored",
        "baseline_mfe_r_mean",
        "baseline_mfe_r_median",
        "baseline_mae_r_mean",
        "baseline_mae_r_median",
        "trailing_mfe_r_mean",
        "trailing_mfe_r_median",
        "trailing_mae_r_mean",
        "trailing_mae_r_median",
        "trailing_stop_exit_r_mean",
        "trailing_stop_exit_r_median",
        "performance_validated",
    ]
    for key in keys:
        print(f"{key}=", report[key])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
