"""
Brooks Structural Trailing Diagnostics V3 — research/diagnostic only.
Does not modify V2.1, RC54.3.2, Score, Risk, Decision, Alert or execution.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path
from analysis.price_action.protective_trailing_stop_dynamics import ProtectiveTrailingStopDynamics
from tools import profit_rtd_brooks_structural_advance_gate_diagnostics_v2_1 as v2

STAGE = "BROOKS_STRUCTURAL_TRAILING_DIAGNOSTICS_V3"
_ENGINE = ProtectiveTrailingStopDynamics()

def _safety():
    return dict(research_only=True, diagnostic_only=True, observational_only=True,
        source_session_validity_changed=False, selection_eligibility_changed=False,
        oos_eligibility_changed=False, predictive_claim_allowed=False,
        score_influence_allowed=False, risk_influence_allowed=False,
        decision_influence_allowed=False, alert_influence_allowed=False,
        order_execution_allowed=False, performance_validated=False,
        promotion_allowed=False, hypothesis_freeze_allowed=False)

def _load(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def _candidate(direction, swing, tick):
    if swing is None: return None
    return float(swing)-tick if direction=="BUY" else float(swing)+tick

def _relation(direction, value, current):
    if value is None: return "NOT_AVAILABLE"
    if value == current: return "EQUAL"
    if direction=="BUY": return "TIGHTER" if value > current else "LOOSER"
    return "TIGHTER" if value < current else "LOOSER"

def _blocked(g, e):
    if not g["history_ready"]: return "INSUFFICIENT_HISTORY"
    if not g["pivot_any"]: return "NO_CONFIRMED_PIVOT"
    if not g["reference_swing_present"]: return "NO_REFERENCE_SWING"
    if not g["prior_opposite_pivot_present"]: return "NO_PRIOR_OPPOSITE_PIVOT"
    if not g["later_opposite_pivot_present"]: return "NO_LATER_OPPOSITE_PIVOT"
    if not g["both_sides_present"]: return "INCOMPLETE_STRUCTURAL_SIDES"
    if not g["breakout_confirmed"]: return "STRUCTURAL_BREAKOUT_NOT_CONFIRMED"
    if e["stop_loosened"]: return "CURRENT_STOP_LOOSER_THAN_INITIAL"
    if not e["structural_advance_confirmed"]: return "V2_ENGINE_STRUCTURAL_MISMATCH"
    if not e["stop_improved"]: return "STRUCTURAL_ADVANCE_BUT_NO_TIGHTER_STOP"
    if e["state"] != "TRAILING_STOP_ADVANCE": return "IMPROVED_BUT_STATE_NOT_ADVANCE"
    return "ADVANCE"

def diagnose_session(payload, tick_size=1.0):
    raw = payload.get("samples") or []
    samples = v2._deduplicate(raw)
    candles = [v2._to_candle(x) for x in samples]
    counts, states, blocked, mismatch = Counter(), Counter(), Counter(), Counter()
    cases, advances = [], []
    episodes = 0

    for ei, sample in enumerate(samples):
        entry = v2._eligible_entry(sample)
        if entry is None: continue
        episodes += 1
        d = entry["direction"]
        initial = float(entry["initial_stop"])
        current = initial

        for oi in range(ei+1, len(samples)):
            hist = list(candles[:oi+1])
            hist.append(v2._synthetic_sentinel(candles[oi]))
            g = v2._gate_analysis(hist, d)
            before = current
            er = _ENGINE.analyze(hist, d, float(entry["entry_price"]),
                                 initial, current_stop=before, tick_size=tick_size)
            e = er.to_dict()
            cand = _candidate(d, g["reference_swing_price"], tick_size) if g["breakout_confirmed"] else None
            rel = _relation(d, cand, before)

            counts["observations"] += 1
            counts[f"{d.lower()}_observations"] += 1
            for k in ("history_ready","pivot_any","reference_swing_present",
                      "prior_opposite_pivot_present","later_opposite_pivot_present",
                      "both_sides_present","breakout_confirmed"):
                if g[k]:
                    counts[k] += 1
                    counts[f"{d.lower()}_{k}"] += 1

            if cand is not None: counts["candidate_stop_available"] += 1
            if rel=="TIGHTER": counts["candidate_tighter_than_current"] += 1
            elif rel=="EQUAL": counts["candidate_equal_current"] += 1
            elif rel=="LOOSER": counts["candidate_looser_than_current"] += 1

            if e["structural_advance_confirmed"]: counts["engine_structural_confirmed"] += 1
            if e["stop_improved"]: counts["engine_stop_improved"] += 1
            if e["stop_loosened"]: counts["engine_stop_loosened"] += 1
            states[e["state"]] += 1

            structural_match = bool(g["breakout_confirmed"]) == bool(e["structural_advance_confirmed"])
            if not structural_match: mismatch["structural_confirmation_mismatch"] += 1

            proposed = float(e["proposed_stop"])
            actual = e["state"] == "TRAILING_STOP_ADVANCE"
            expected = bool(e["structural_advance_confirmed"]) and not bool(e["stop_loosened"]) and (
                proposed > before if d=="BUY" else proposed < before)
            if expected != actual: mismatch["expected_actual_advance_mismatch"] += 1

            revision = False
            if actual and ((d=="BUY" and proposed>before) or (d=="SELL" and proposed<before)):
                current = proposed
                revision = True
                counts["stop_revision_applied"] += 1
            if actual: counts["actual_trailing_stop_advance"] += 1
            if expected: counts["expected_trailing_stop_advance"] += 1
            if g["breakout_confirmed"] and e["structural_advance_confirmed"] and not e["stop_improved"]:
                counts["structural_but_not_tighter"] += 1

            reason = _blocked(g, e)
            blocked[reason] += 1
            row = dict(direction=d, entry_candle_id=v2._candle_id(sample),
                observation_candle_id=v2._candle_id(samples[oi]),
                observation_exact_index=oi, entry_price=float(entry["entry_price"]),
                initial_stop=initial, current_stop_before=before, current_stop_after=current,
                tick_size=float(tick_size), reference_swing_index=g["reference_swing_index"],
                reference_swing_price=g["reference_swing_price"],
                prior_opposite_price=g["prior_opposite_price"],
                later_opposite_price=g["later_opposite_price"],
                breakout_distance=g["breakout_distance"],
                v2_breakout_confirmed=bool(g["breakout_confirmed"]),
                candidate_stop=cand, candidate_vs_current=rel,
                engine_state=e["state"], engine_reason=e["reason"],
                engine_structural_advance_confirmed=bool(e["structural_advance_confirmed"]),
                engine_trailing_active=bool(e["trailing_active"]),
                engine_proposed_stop=proposed, engine_stop_improved=bool(e["stop_improved"]),
                engine_stop_loosened=bool(e["stop_loosened"]),
                expected_trailing_stop_advance=expected,
                actual_trailing_stop_advance=actual, revision_applied=revision,
                structural_confirmation_match=structural_match, blocked_reason=reason)
            if g["breakout_confirmed"]: cases.append(row)
            if actual: advances.append(row)

    return dict(raw_samples=len(raw), exact_candles=len(samples),
        eligible_entry_episodes=episodes, observation_count=counts["observations"],
        counts=dict(sorted(counts.items())), engine_state_counts=dict(sorted(states.items())),
        blocked_reason_counts=dict(sorted(blocked.items())),
        mismatch_counts=dict(sorted(mismatch.items())),
        structural_case_count=len(cases), advance_case_count=len(advances),
        structural_cases=cases, advance_cases=advances)

def diagnose_many(paths, tick_size=1.0):
    sessions=[]; totals=Counter(); states=Counter(); blocked=Counter(); mismatch=Counter()
    structural=[]; advances=[]
    raw=exact=episodes=obs=0
    for i,p in enumerate(paths):
        r=diagnose_session(_load(p), tick_size)
        r["session_index"]=i; r["source"]=str(p); sessions.append(r)
        raw+=r["raw_samples"]; exact+=r["exact_candles"]; episodes+=r["eligible_entry_episodes"]; obs+=r["observation_count"]
        totals.update(r["counts"]); states.update(r["engine_state_counts"])
        blocked.update(r["blocked_reason_counts"]); mismatch.update(r["mismatch_counts"])
        structural += [dict(session_index=i, source=str(p), **x) for x in r["structural_cases"]]
        advances += [dict(session_index=i, source=str(p), **x) for x in r["advance_cases"]]
    return dict(status="COMPLETED", stage=STAGE, structural_reference_stage=v2.STAGE,
        deduplication=v2.DEDUPLICATION, tick_size=float(tick_size),
        accepted_session_count=len(sessions), raw_samples=raw, exact_candles=exact,
        eligible_entry_episodes=episodes, observation_count=obs,
        counts=dict(sorted(totals.items())), engine_state_counts=dict(sorted(states.items())),
        blocked_reason_counts=dict(sorted(blocked.items())),
        mismatch_counts=dict(sorted(mismatch.items())),
        structural_case_count=len(structural), advance_case_count=len(advances),
        structural_cases=structural, advance_cases=advances, sessions=sessions, **_safety())

def main(argv=None):
    ap=argparse.ArgumentParser(description="Brooks Structural Trailing Diagnostics V3")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--output")
    ap.add_argument("--tick-size", type=float, default=1.0)
    a=ap.parse_args(argv)
    r=diagnose_many(a.paths, a.tick_size)
    if a.output:
        o=Path(a.output); o.parent.mkdir(parents=True, exist_ok=True)
        o.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    for k in ("status","stage","accepted_session_count","raw_samples","exact_candles",
              "eligible_entry_episodes","observation_count","structural_case_count","advance_case_count"):
        print(f"{k}=", r[k])
    for k in ("counts","engine_state_counts","blocked_reason_counts","mismatch_counts"):
        print(f"{k}=", json.dumps(r[k], ensure_ascii=False, sort_keys=True))
    print("research_only=", r["research_only"])
    print("source_session_validity_changed=", r["source_session_validity_changed"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
