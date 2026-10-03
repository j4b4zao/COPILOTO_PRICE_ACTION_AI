"""Fixed-cohort descriptive consolidation of five official RC1 evaluator JSONs."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from tools.rc17_sideways_to_directional_evolution_evaluator import VERSION as EVALUATOR_VERSION
from tools.rc17_sideways_to_directional_evolution_protocol_validator import (
    EXPECTED_VERSION, EXPECTED_SHA256, PROTOCOL_PATH, validate,
)

VERSION = "RC1-RC17-SIDEWAYS-TO-DIRECTIONAL-EVOLUTION-CONSOLIDATION"
SESSION_IDS = (19, 20, 21, 22, 23)
CLASSIFICATIONS = ("DIRECTIONAL_TRANSITION_OBSERVED",
                   "NO_DIRECTIONAL_TRANSITION_OBSERVED", "CAPTURE_INTEGRITY_FAILURE")
STATES = ("SIDEWAYS", "UP", "DOWN")
TRANSITIONS = tuple(a + "_TO_" + b for a in STATES for b in STATES)
UNKNOWN_TRANSITIONS = tuple(a + "_TO_" + b for a in (*STATES, "UNKNOWN")
                            for b in (*STATES, "UNKNOWN") if "UNKNOWN" in (a, b))
FLAGS = dict(research_only=True, descriptive_only=True, predictive_validation=False,
             causal_validation=False, operational_promotion=False, threshold_optimization=False)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def count(value):
    return type(value) is int and value >= 0


def count_map(value, name, required=(), allowed=None):
    require(isinstance(value, dict) and all(k in value for k in required), name + " missing")
    require(all(isinstance(k, str) and count(v) for k, v in value.items()), name + " invalid counts")
    if allowed is not None:
        require(set(value) <= set(allowed), name + " unknown keys")


def checked_session(payload):
    require(isinstance(payload, dict), "result must be an object")
    sid = payload.get("session_id")
    require(type(sid) is int and sid in SESSION_IDS, "session outside fixed cohort")
    require(payload.get("evaluator_version") == EVALUATOR_VERSION, "evaluator version mismatch")
    protocol = payload.get("protocol")
    require(isinstance(protocol, dict) and protocol.get("version") == EXPECTED_VERSION
            and protocol.get("sha256") == EXPECTED_SHA256, "protocol identity mismatch")
    for key, expected in FLAGS.items():
        require(payload.get(key) is expected, "research flag mismatch: " + key)
    raw = payload.get("raw")
    require(isinstance(raw, dict), "raw identity missing")
    for key in ("path", "filename"):
        require(isinstance(raw.get(key), str) and bool(raw[key].strip()), "raw " + key + " missing")
    require(isinstance(raw.get("sha256"), str) and re.fullmatch(r"[0-9a-fA-F]{64}", raw["sha256"]),
            "raw SHA256 missing or malformed")
    require(count(raw.get("size")), "raw size invalid")
    classification = payload.get("session_classification")
    require(classification in CLASSIFICATIONS, "unknown classification")
    capture = payload.get("capture_summary")
    require(isinstance(capture, dict), "capture summary missing")
    for key in ("requested_cycles", "total_cycles", "analyzable_samples", "skipped_cycles", "errors"):
        require(key in capture and (count(capture[key]) or
                classification == "CAPTURE_INTEGRITY_FAILURE" and capture[key] is None),
                "capture count missing or invalid: " + key)
    states = payload.get("state_counts")
    require(isinstance(states, dict), "state counts missing")
    count_map(states.get("TREND_COUNTS"), "trend counts", (*STATES, "UNKNOWN"), (*STATES, "UNKNOWN"))
    count_map(states.get("PA_BIAS_COUNTS"), "PA bias counts", ("BUY", "SELL", "NONE"), ("BUY", "SELL", "NONE"))
    for key in ("total_analyzed_samples", "sideways_none_samples", "up_buy_samples",
                "down_sell_samples", "unknown_none_samples"):
        require(count(states.get(key)), "state count invalid: " + key)
    swing_keys = ("SAMPLES_WITH_HIGH_ONLY", "SAMPLES_WITH_LOW_ONLY",
                  "SAMPLES_WITH_BOTH_SWING_TYPES", "SAMPLES_WITH_NO_SWINGS")
    count_map(payload.get("swing_state_counts"), "swing counts", swing_keys, swing_keys)
    count_map(payload.get("transition_counts"), "transitions", TRANSITIONS[:3], TRANSITIONS)
    count_map(payload.get("unknown_transition_counts"), "unknown transitions",
              UNKNOWN_TRANSITIONS, UNKNOWN_TRANSITIONS)
    require(count(payload.get("primary_event_count")), "primary event count invalid")
    # Preserve evaluator decisions and integrity evidence, including events in failed captures.
    keys = ("session_id", "raw", "capture_summary", "state_counts", "swing_state_counts",
            "transition_counts", "unknown_transition_counts", "primary_event_count",
            "session_classification", "integrity")
    return copy.deepcopy({key: payload[key] for key in keys if key in payload})


def consolidate(result_paths, protocol_path=PROTOCOL_PATH):
    """Require exactly five explicit evaluator paths; never resolve or open raw paths."""
    paths = [Path(path) for path in result_paths]
    require(len(paths) == 5, "exactly five explicit result paths required")
    require(len({p.resolve() for p in paths}) == 5, "duplicate result path")
    protocol = validate(protocol_path)
    require(protocol["status"] == "PASS", "protocol validator failed")
    sessions, sources = [], []
    for path in paths:
        data = path.read_bytes()
        payload = json.loads(data.decode("utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(
            ValueError("nonfinite JSON: " + x)))
        session = checked_session(payload)
        sessions.append(session)
        sources.append(dict(session_id=session["session_id"], path=str(path),
                            sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
    require(sorted(s["session_id"] for s in sessions) == list(SESSION_IDS),
            "duplicate or missing session in fixed cohort")
    sessions.sort(key=lambda s: s["session_id"])
    sources.sort(key=lambda s: s["session_id"])
    totals = {key: sum(s["transition_counts"][key] for s in sessions)
              for key in TRANSITIONS if all(key in s["transition_counts"] for s in sessions)}
    unknown = {key: sum(s["unknown_transition_counts"][key] for s in sessions)
               for key in UNKNOWN_TRANSITIONS}
    return dict(consolidator_version=VERSION,
        protocol=dict(version=EXPECTED_VERSION, sha256=EXPECTED_SHA256),
        cohort=dict(fixed_session_ids=list(SESSION_IDS), planned_sessions=5,
                    completed_sessions=5, block_status="COMPLETE"),
        sessions=sessions, result_sources=sources,
        descriptive_counts=dict(
            directional_transition_observed_sessions=sum(s["session_classification"] == CLASSIFICATIONS[0] for s in sessions),
            no_directional_transition_observed_sessions=sum(s["session_classification"] == CLASSIFICATIONS[1] for s in sessions),
            capture_integrity_failure_sessions=sum(s["session_classification"] == CLASSIFICATIONS[2] for s in sessions),
            total_primary_events=sum(s["primary_event_count"] for s in sessions)),
        transition_totals=totals, unknown_transition_totals=unknown,
        interpretation=dict(**FLAGS, raw_pooling=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for sid in SESSION_IDS:
        parser.add_argument(f"--session{sid}-result", required=True)
    parser.add_argument("--protocol-path", default=str(PROTOCOL_PATH))
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args(argv)
    try:
        paths = [getattr(args, f"session{sid}_result") for sid in SESSION_IDS]
        result = consolidate(paths, args.protocol_path)
        # Named CLI slots must match their explicit session IDs.
        for sid, path in zip(SESSION_IDS, paths):
            source = next(s for s in result["result_sources"] if s["session_id"] == sid)
            require(source["path"] == str(Path(path)), "CLI session slot mismatch")
        with Path(args.output_path).open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    except (ValueError, OSError, TypeError) as exc:
        print("ABORT: " + str(exc))
        return 2
    print("BLOCK_STATUS=COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
