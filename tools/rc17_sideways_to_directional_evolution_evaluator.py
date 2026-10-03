"""Offline descriptive RC1 evaluation of persisted official results only."""
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from tools.rc17_sideways_to_directional_evolution_protocol_validator import validate

VERSION = "RC1-RC17-SIDEWAYS-TO-DIRECTIONAL-EVOLUTION-EVALUATOR"
TRENDS = ("UP", "DOWN", "SIDEWAYS", "UNKNOWN")
FLAGS = {"hh": "higher_high", "hl": "higher_low",
         "lh": "lower_high", "ll": "lower_low"}


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp missing")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sample_errors(sample, symbol):
    errors = []
    def require(condition, reason):
        if not condition:
            errors.append(reason)
    try:
        s = sample["structure"]
        bias = sample["price_action"]["bias"]
        require(s["trend"] in TRENDS, "official trend invalid")
        require(bias in ("BUY", "SELL", "NONE"), "official bias invalid")
        require(type(s["valid"]) is bool, "official valid invalid")
        for flag in FLAGS:
            require(type(s[flag]) is bool, "official flag invalid: " + flag)
        if s["trend"] == "UP":
            require(s["hh"] is True and s["hl"] is True, "UP without HH+HL")
        if s["trend"] == "DOWN":
            require(s["lh"] is True and s["ll"] is True, "DOWN without LH+LL")
        d = sample["market_structure_observability"]
        require(d["guard_status"] in ("EXECUTED", "SKIPPED"), "diagnostic unavailable")
        require(d["engine_version"] == "RC17-CLOSED-CANDLE", "engine mismatch")
        require(d["history_unchanged_during_pipeline"] is True, "history changed")
        require(d["cycle"] == sample["cycle"] and d["timestamp"] == sample["timestamp"], "diagnostic identity mismatch")
        require(d["symbol"] == symbol, "symbol mismatch")
        closed = d["closed_candles"]
        require(isinstance(closed, list), "closed history invalid")
        require(type(d["closed_candle_count"]) is int and d["closed_candle_count"] == len(closed), "closed count mismatch")
        require([c["index"] for c in closed] == list(range(len(closed)))
                and all(type(c["index"]) is int for c in closed), "closed indexes invalid")
        digest = d["closed_history_sha256"]
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-fA-F]{64}", digest) is not None
                and digest.lower() == _hash(_canonical(closed)), "closed history hash invalid")
        forming = d["excluded_forming_candle"]
        require(isinstance(forming, dict) and type(forming["index"]) is int
                and forming["index"] == len(closed) and forming not in closed,
                "forming candle not separated")
        require(d["total_candle_count"] == len(closed) + 1, "total candle count mismatch")
        times = [_timestamp(c["timestamp"]) for c in closed] + [_timestamp(forming["timestamp"])]
        require(all(a < b for a, b in zip(times, times[1:])), "candle chronology invalid")
        for kind, field in (("high", "high"), ("low", "low")):
            swings = d["swing_" + kind + "s"]
            require(isinstance(swings, list), "swings invalid")
            count = d["swing_" + kind + "_count"]
            require(type(count) is int and count == len(swings), "swing count mismatch")
            indices = [x["history_index"] for x in swings]
            require(all(type(i) is int and 2 <= i < len(closed) - 2 for i in indices)
                    and all(a < b for a, b in zip(indices, indices[1:])), "swing indexes invalid")
            for swing in swings:
                candle = closed[swing["history_index"]]
                require(swing["timestamp"] == candle["timestamp"] and swing["price"] == candle[field], "swing reference mismatch")
            require(d["latest_swing_" + kind] == (swings[-1] if swings else None), "latest swing mismatch")
            require(d["previous_swing_" + kind] == (swings[-2] if len(swings) > 1 else None), "previous swing mismatch")
        observed = d["observed_result"]
        for field in ("trend", "valid", "bos_up", "bos_down", "choch"):
            require(type(observed[field]) is type(s[field]) and observed[field] == s[field], "diagnostic result mismatch: " + field)
        for flag, diagnostic_flag in FLAGS.items():
            require(type(observed[diagnostic_flag]) is bool and observed[diagnostic_flag] == s[flag], "diagnostic flag mismatch: " + flag)
        # Snapshot serialization maps nullable official levels to 0.0.
        for field in ("last_high", "last_low"):
            require(s[field] == (observed[field] if observed[field] is not None else 0.0), "diagnostic level mismatch: " + field)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        errors.append("missing or malformed evidence: " + str(exc))
    return errors


def _snapshot(sample):
    s, d = sample["structure"], sample["market_structure_observability"]
    return {"cycle": sample["cycle"], "timestamp": sample["timestamp"],
            "trend": s["trend"], "price_action_bias": sample["price_action"]["bias"],
            "valid": s["valid"], **{k.upper(): s[k] for k in FLAGS},
            **{k: d[k] for k in ("swing_high_count", "swing_low_count", "latest_swing_high",
                "previous_swing_high", "latest_swing_low", "previous_swing_low", "closed_history_sha256")}}


def evaluate(raw_path, session_id, protocol_path, output_path=None):
    if type(session_id) is not int or session_id not in range(19, 24):
        raise ValueError("session_id must be an explicit integer in 19..23")
    protocol = validate(protocol_path)
    path = Path(raw_path)
    if output_path is not None:
        target = Path(output_path)
        if target.resolve() in (path.resolve(), Path(protocol_path).resolve()) or (
                target.exists() and (target.samefile(path) or target.samefile(protocol_path))):
            raise ValueError("output must not overwrite raw or protocol")
    data = path.read_bytes()
    before = _hash(data)
    raw = json.loads(data.decode("utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON: " + x)))
    if not isinstance(raw, dict) or not isinstance(raw.get("samples"), list):
        raise ValueError("raw must contain a persisted samples list")
    samples = raw["samples"]
    errors, events = [], []
    trends = dict.fromkeys(TRENDS, 0)
    biases = dict.fromkeys(("BUY", "SELL", "NONE"), 0)
    paired_states = dict.fromkeys(("sideways_none_samples", "up_buy_samples",
                                  "down_sell_samples", "unknown_none_samples"), 0)
    swings = dict.fromkeys(("SAMPLES_WITH_HIGH_ONLY", "SAMPLES_WITH_LOW_ONLY",
                           "SAMPLES_WITH_BOTH_SWING_TYPES", "SAMPLES_WITH_NO_SWINGS"), 0)
    transitions = {a + "_TO_" + b: 0 for a in TRENDS if a != "UNKNOWN" for b in TRENDS if b != "UNKNOWN"}
    unknown = {a + "_TO_" + b: 0 for a in TRENDS for b in TRENDS if "UNKNOWN" in (a, b)}
    counts = [raw.get(k) for k in ("requested_cycles", "analyzable_samples", "skipped_cycles", "collection_errors")]
    if not isinstance(raw.get("symbol"), str) or not raw["symbol"].strip():
        errors.append({"scope": "capture", "reasons": ["symbol missing or invalid"]})
    if not all(type(v) is int and v >= 0 for v in counts) or counts[1] != len(samples) or counts[0] != sum(counts[1:]):
        errors.append({"scope": "capture", "reasons": ["cycle accounting invalid"]})
    previous = None
    last_cycle = last_time = None
    for position, sample in enumerate(samples):
        reasons = _sample_errors(sample, raw.get("symbol"))
        try:
            cycle, timestamp = sample["cycle"], _timestamp(sample["timestamp"])
            if type(cycle) is not int or cycle < 1 or (type(counts[0]) is int and cycle > counts[0]) or (last_cycle is not None and cycle <= last_cycle) or (last_time is not None and timestamp < last_time):
                reasons.append("sample chronology invalid")
            last_cycle, last_time = cycle, timestamp
        except (KeyError, TypeError, ValueError):
            reasons.append("sample chronology missing or malformed")
        s = sample.get("structure", {}) if isinstance(sample, dict) else {}
        b = sample.get("price_action", {}) if isinstance(sample, dict) else {}
        s = s if isinstance(s, dict) else {}
        b = b if isinstance(b, dict) else {}
        if isinstance(s.get("trend"), str) and s["trend"] in trends:
            trends[s["trend"]] += 1
        if isinstance(b.get("bias"), str) and b["bias"] in biases:
            biases[b["bias"]] += 1
        paired_key = {("SIDEWAYS", "NONE"): "sideways_none_samples",
                      ("UP", "BUY"): "up_buy_samples", ("DOWN", "SELL"): "down_sell_samples",
                      ("UNKNOWN", "NONE"): "unknown_none_samples"}.get((s.get("trend"), b.get("bias"))) if isinstance(s.get("trend"), str) and isinstance(b.get("bias"), str) else None
        if paired_key:
            paired_states[paired_key] += 1
        if reasons:
            errors.append({"sample_position": position, "reasons": reasons})
            previous = None
            continue
        d = sample["market_structure_observability"]
        high, low = bool(d["swing_high_count"]), bool(d["swing_low_count"])
        key = "SAMPLES_WITH_BOTH_SWING_TYPES" if high and low else "SAMPLES_WITH_HIGH_ONLY" if high else "SAMPLES_WITH_LOW_ONLY" if low else "SAMPLES_WITH_NO_SWINGS"
        swings[key] += 1
        if previous is not None:
            a, z = previous["structure"]["trend"], s["trend"]
            key = a + "_TO_" + z
            (unknown if "UNKNOWN" in (a, z) else transitions)[key] += 1
            if a == "SIDEWAYS" and previous["structure"]["valid"] is True and previous["price_action"]["bias"] == "NONE" and ((z == "UP" and b["bias"] == "BUY") or (z == "DOWN" and b["bias"] == "SELL")):
                events.append({"from_cycle": previous["cycle"], "to_cycle": sample["cycle"],
                    "from_timestamp": previous["timestamp"], "to_timestamp": sample["timestamp"],
                    "before": _snapshot(previous), "after": _snapshot(sample)})
        previous = sample
    after = _hash(path.read_bytes())
    if before != after:
        errors.append({"scope": "raw", "reasons": ["raw changed during evaluation"]})
    result = {"evaluator_version": VERSION, "session_id": session_id,
        "protocol": {"version": protocol["protocol_version"], "sha256": protocol["protocol_sha256"]},
        "raw": {"path": str(path), "filename": path.name, "sha256": before, "size": len(data)},
        "capture_summary": {"symbol": raw.get("symbol"), "requested_cycles": counts[0],
            "total_cycles": sum(counts[1:]) if all(type(v) is int for v in counts[1:]) else None,
            "analyzable_samples": counts[1], "skipped_cycles": counts[2], "errors": counts[3]},
        "integrity": {"valid": not errors, "failures": errors, "raw_sha_before": before,
            "raw_sha_after": after, "raw_unchanged": before == after},
        "state_counts": {"TREND_COUNTS": trends, "PA_BIAS_COUNTS": biases,
                         "total_analyzed_samples": len(samples), **paired_states},
        "swing_state_counts": swings, "transition_counts": transitions, "unknown_transition_counts": unknown,
        "primary_event_count": len(events), "primary_events": events,
        "session_classification": "CAPTURE_INTEGRITY_FAILURE" if errors else
            "DIRECTIONAL_TRANSITION_OBSERVED" if events else "NO_DIRECTIONAL_TRANSITION_OBSERVED",
        "research_only": True, "descriptive_only": True, "predictive_validation": False,
        "causal_validation": False, "operational_promotion": False, "threshold_optimization": False}
    if output_path is not None:
        Path(output_path).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-path", required=True)
    parser.add_argument("--session-id", type=int, required=True, choices=range(19, 24))
    parser.add_argument("--protocol-path", required=True)
    parser.add_argument("--output-path")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.raw_path, args.session_id, args.protocol_path, args.output_path), indent=2))


if __name__ == "__main__":
    main()
