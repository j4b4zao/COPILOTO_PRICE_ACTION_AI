"""
tools/profit_rtd_brooks_management_intrabar_bounded_outcome.py

Stage 3.3 — Brooks Intrabar-Bounded Outcome Audit.

Corrige duas ambiguidades da Stage 3.2:
1) episodios sem qualquer candle posterior a entrada passam a ser classificados
   explicitamente como NO_POST_ENTRY_EVIDENCE;
2) no candle de stop, a ordem intrabar e desconhecida em dados OHLC.
   Portanto:
   - MAE realizado fica limitado ao stop ativo daquele modelo;
   - MFE confirmado usa somente candles anteriores ao candle de saida;
   - MFE possivel inclui o extremo favoravel do candle de saida, mas e
     explicitamente marcado como intrabar-ambiguous.

Nao declara performance, edge ou vantagem operacional.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

SETUP_NAME = "BROOKS_MANAGEMENT_INTRABAR_BOUNDED_OUTCOME_V1"
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
    evidence = sample.get("candle_evidence") or {}
    return {
        "candle_id": str(evidence.get("candle_id") or ""),
        "high": _f(evidence.get("high")),
        "low": _f(evidence.get("low")),
        "close": _f(evidence.get("close")),
    }


def _risk(direction, entry, stop):
    if direction == "BUY":
        return entry - stop
    if direction == "SELL":
        return stop - entry
    return 0.0


def _favorable_r(direction, entry, candle, risk):
    if direction == "BUY":
        return max(0.0, (candle["high"] - entry) / risk)
    return max(0.0, (entry - candle["low"]) / risk)


def _adverse_r(direction, entry, candle, risk):
    if direction == "BUY":
        return max(0.0, (entry - candle["low"]) / risk)
    return max(0.0, (candle["high"] - entry) / risk)


def _stop_hit(direction, candle, stop):
    if direction == "BUY":
        return candle["low"] <= stop + EPS
    if direction == "SELL":
        return candle["high"] >= stop - EPS
    return False


def _stop_r(direction, entry, initial_stop, active_stop):
    risk = _risk(direction, entry, initial_stop)
    if risk <= EPS:
        return 0.0

    if direction == "BUY":
        return (active_stop - entry) / risk

    return (entry - active_stop) / risk


def _close_r(direction, entry, initial_stop, close):
    risk = _risk(direction, entry, initial_stop)
    if risk <= EPS:
        return 0.0

    if direction == "BUY":
        return (close - entry) / risk

    return (entry - close) / risk


def _new_track():
    return {
        "status": "OPEN",
        "exit_type": None,
        "exit_candle_id": None,
        "exit_exact_index": None,
        "exit_r": None,
        "confirmed_mfe_r": 0.0,
        "possible_mfe_r": 0.0,
        "bounded_mae_r": 0.0,
        "exit_candle_intrabar_ambiguous": False,
    }


def analyze_episode(episode, exact_samples):
    direction = str(episode.get("direction") or "").upper()
    entry = _f(episode.get("entry_price"))
    initial_stop = _f(episode.get("initial_stop"))
    entry_cid = str(episode.get("entry_event_candle_id") or "")

    index_by_id = {}
    for idx, sample in enumerate(exact_samples):
        cid = _candle(sample)["candle_id"]
        if cid:
            index_by_id[cid] = idx

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

    if entry_idx >= len(exact_samples) - 1:
        return {
            "episode_id": episode.get("episode_id"),
            "entry_event_candle_id": entry_cid,
            "direction": direction,
            "entry_price": entry,
            "initial_stop": initial_stop,
            "initial_risk_points": risk,
            "eligible": True,
            "status": "NO_POST_ENTRY_EVIDENCE",
            "baseline": {
                **_new_track(),
                "status": "NO_POST_ENTRY_EVIDENCE",
            },
            "trailing": {
                **_new_track(),
                "status": "NO_POST_ENTRY_EVIDENCE",
            },
        }

    observations = {
        int(obs["observation_exact_index"]): obs
        for obs in (episode.get("observations") or [])
        if isinstance(obs, dict)
        and obs.get("observation_exact_index") is not None
    }

    baseline = _new_track()
    trailing = _new_track()

    active_trailing_stop = initial_stop
    last_candle = None

    for idx in range(entry_idx + 1, len(exact_samples)):
        candle = _candle(exact_samples[idx])
        last_candle = candle

        favorable = _favorable_r(
            direction, entry, candle, risk
        )
        adverse = _adverse_r(
            direction, entry, candle, risk
        )

        # BASELINE
        if baseline["status"] == "OPEN":
            baseline_hit = _stop_hit(
                direction,
                candle,
                initial_stop,
            )

            if baseline_hit:
                # MFE deste candle e apenas possivel: ordem intrabar desconhecida.
                baseline["possible_mfe_r"] = max(
                    baseline["confirmed_mfe_r"],
                    favorable,
                )
                baseline["bounded_mae_r"] = max(
                    baseline["bounded_mae_r"],
                    1.0,
                )
                baseline["status"] = "EXITED"
                baseline["exit_type"] = "INITIAL_STOP"
                baseline["exit_candle_id"] = candle["candle_id"]
                baseline["exit_exact_index"] = idx
                baseline["exit_r"] = -1.0
                baseline["exit_candle_intrabar_ambiguous"] = True
            else:
                baseline["confirmed_mfe_r"] = max(
                    baseline["confirmed_mfe_r"],
                    favorable,
                )
                baseline["possible_mfe_r"] = (
                    baseline["confirmed_mfe_r"]
                )
                baseline["bounded_mae_r"] = max(
                    baseline["bounded_mae_r"],
                    adverse,
                )

        # TRAILING
        if trailing["status"] == "OPEN":
            trailing_hit = _stop_hit(
                direction,
                candle,
                active_trailing_stop,
            )

            if trailing_hit:
                active_stop_r = _stop_r(
                    direction,
                    entry,
                    initial_stop,
                    active_trailing_stop,
                )
                max_adverse_to_stop = max(
                    0.0,
                    -active_stop_r,
                )

                trailing["possible_mfe_r"] = max(
                    trailing["confirmed_mfe_r"],
                    favorable,
                )
                trailing["bounded_mae_r"] = max(
                    trailing["bounded_mae_r"],
                    max_adverse_to_stop,
                )
                trailing["status"] = "EXITED"
                trailing["exit_type"] = "TRAILING_STOP"
                trailing["exit_candle_id"] = candle["candle_id"]
                trailing["exit_exact_index"] = idx
                trailing["exit_stop"] = active_trailing_stop
                trailing["exit_r"] = active_stop_r
                trailing["exit_candle_intrabar_ambiguous"] = True
            else:
                trailing["confirmed_mfe_r"] = max(
                    trailing["confirmed_mfe_r"],
                    favorable,
                )
                trailing["possible_mfe_r"] = (
                    trailing["confirmed_mfe_r"]
                )
                trailing["bounded_mae_r"] = max(
                    trailing["bounded_mae_r"],
                    adverse,
                )

        # Revisao observada no candle N vale apenas em N+1.
        if trailing["status"] == "OPEN":
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

        if (
            baseline["status"] == "EXITED"
            and trailing["status"] == "EXITED"
        ):
            break

    # Caminhos ainda abertos no final ficam censurados.
    if last_candle is not None:
        if baseline["status"] == "OPEN":
            baseline["status"] = "CENSORED"
            baseline["exit_type"] = "SESSION_END_CENSORED"
            baseline["exit_candle_id"] = last_candle["candle_id"]
            baseline["exit_exact_index"] = len(exact_samples) - 1
            baseline["session_end_mark_r"] = _close_r(
                direction,
                entry,
                initial_stop,
                last_candle["close"],
            )

        if trailing["status"] == "OPEN":
            trailing["status"] = "CENSORED"
            trailing["exit_type"] = "SESSION_END_CENSORED"
            trailing["exit_candle_id"] = last_candle["candle_id"]
            trailing["exit_exact_index"] = len(exact_samples) - 1
            trailing["session_end_mark_r"] = _close_r(
                direction,
                entry,
                initial_stop,
                last_candle["close"],
            )

    return {
        "episode_id": episode.get("episode_id"),
        "entry_event_candle_id": entry_cid,
        "direction": direction,
        "entry_price": entry,
        "initial_stop": initial_stop,
        "initial_risk_points": risk,
        "eligible": True,
        "status": "INTRABAR_BOUNDED_OUTCOME_COMPLETED",
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
            "INTRABAR_BOUNDED_SESSION_COMPLETED"
            if eligible
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "source": source,
        "exact_candles": len(exact_samples),
        "eligible_episodes": len(eligible),
        "episodes": episodes,
        **_safety(),
    }


def analyze_many(lifecycle_payload):
    sessions = [
        analyze_session(session)
        for session in (lifecycle_payload.get("sessions") or [])
        if isinstance(session, dict)
    ]

    episodes = [
        ep
        for session in sessions
        for ep in session.get("episodes") or []
        if ep.get("eligible")
    ]

    no_post = [
        ep for ep in episodes
        if ep.get("status") == "NO_POST_ENTRY_EVIDENCE"
    ]
    observed = [
        ep for ep in episodes
        if ep.get("status") == "INTRABAR_BOUNDED_OUTCOME_COMPLETED"
    ]

    baseline_stop = sum(
        ep["baseline"]["exit_type"] == "INITIAL_STOP"
        for ep in observed
    )
    trailing_stop = sum(
        ep["trailing"]["exit_type"] == "TRAILING_STOP"
        for ep in observed
    )
    baseline_censored = sum(
        ep["baseline"]["exit_type"] == "SESSION_END_CENSORED"
        for ep in observed
    )
    trailing_censored = sum(
        ep["trailing"]["exit_type"] == "SESSION_END_CENSORED"
        for ep in observed
    )

    baseline_confirmed_mfe = [
        ep["baseline"]["confirmed_mfe_r"] for ep in observed
    ]
    baseline_possible_mfe = [
        ep["baseline"]["possible_mfe_r"] for ep in observed
    ]
    baseline_mae = [
        ep["baseline"]["bounded_mae_r"] for ep in observed
    ]

    trailing_confirmed_mfe = [
        ep["trailing"]["confirmed_mfe_r"] for ep in observed
    ]
    trailing_possible_mfe = [
        ep["trailing"]["possible_mfe_r"] for ep in observed
    ]
    trailing_mae = [
        ep["trailing"]["bounded_mae_r"] for ep in observed
    ]

    trailing_exit_rs = [
        ep["trailing"]["exit_r"]
        for ep in observed
        if ep["trailing"]["exit_r"] is not None
    ]

    return {
        "setup": SETUP_NAME,
        "status": (
            "MULTI_SESSION_INTRABAR_BOUNDED_OUTCOME_COMPLETED"
            if episodes
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "accepted_session_count": len(sessions),
        "eligible_episodes": len(episodes),
        "observed_episodes": len(observed),
        "no_post_entry_evidence": len(no_post),
        "baseline_stop_exits": baseline_stop,
        "baseline_censored": baseline_censored,
        "trailing_stop_exits": trailing_stop,
        "trailing_censored": trailing_censored,
        "baseline_confirmed_mfe_r_mean": _mean(
            baseline_confirmed_mfe
        ),
        "baseline_confirmed_mfe_r_median": _median(
            baseline_confirmed_mfe
        ),
        "baseline_possible_mfe_r_mean": _mean(
            baseline_possible_mfe
        ),
        "baseline_possible_mfe_r_median": _median(
            baseline_possible_mfe
        ),
        "baseline_bounded_mae_r_mean": _mean(
            baseline_mae
        ),
        "baseline_bounded_mae_r_median": _median(
            baseline_mae
        ),
        "trailing_confirmed_mfe_r_mean": _mean(
            trailing_confirmed_mfe
        ),
        "trailing_confirmed_mfe_r_median": _median(
            trailing_confirmed_mfe
        ),
        "trailing_possible_mfe_r_mean": _mean(
            trailing_possible_mfe
        ),
        "trailing_possible_mfe_r_median": _median(
            trailing_possible_mfe
        ),
        "trailing_bounded_mae_r_mean": _mean(
            trailing_mae
        ),
        "trailing_bounded_mae_r_median": _median(
            trailing_mae
        ),
        "trailing_stop_exit_r_mean": _mean(
            trailing_exit_rs
        ),
        "trailing_stop_exit_r_median": _median(
            trailing_exit_rs
        ),
        "performance_validated": False,
        "validation_reason": (
            "INTRABAR_ORDER_UNKNOWN_BOUNDED_RESEARCH_ONLY_"
            "NO_PERFORMANCE_CLAIM"
        ),
        "sessions": sessions,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Brooks intrabar-bounded outcome audit."
    )
    parser.add_argument("lifecycle_report")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = analyze_many(_load(args.lifecycle_report))

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    keys = [
        "status",
        "accepted_session_count",
        "eligible_episodes",
        "observed_episodes",
        "no_post_entry_evidence",
        "baseline_stop_exits",
        "baseline_censored",
        "trailing_stop_exits",
        "trailing_censored",
        "baseline_confirmed_mfe_r_mean",
        "baseline_confirmed_mfe_r_median",
        "baseline_possible_mfe_r_mean",
        "baseline_possible_mfe_r_median",
        "baseline_bounded_mae_r_mean",
        "baseline_bounded_mae_r_median",
        "trailing_confirmed_mfe_r_mean",
        "trailing_confirmed_mfe_r_median",
        "trailing_possible_mfe_r_mean",
        "trailing_possible_mfe_r_median",
        "trailing_bounded_mae_r_mean",
        "trailing_bounded_mae_r_median",
        "trailing_stop_exit_r_mean",
        "trailing_stop_exit_r_median",
        "performance_validated",
    ]

    for key in keys:
        print(f"{key}=", report[key])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
