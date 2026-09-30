import hashlib
import json
from pathlib import Path


VERSION = "RC1-PA-BOOK-INDEPENDENT-PROSPECTIVE-REPLICATION-CONSOLIDATION"

PROTOCOL_SHA256 = (
    "53efb327f613934c483f6bec36ffe04bd"
    "98743b2973815f3b54ec2b84e91f01c"
)

EXPECTED = {
    "11": {
        "raw_sha256": "429862d7201dd6db119ec67c67a4e0a1464ba34ac47de4dedbe83416a3da6932",
        "result_path": "pa_book_structural_replication_session11_rc12_20260930.json",
        "expected_outcome": "NOT_EVALUABLE",
        "expected_reason": "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    },
    "12": {
        "raw_sha256": "a6fc5e9df5d00bbb504018b24c9d0eff044a72a03fcb2282f71c73625be47b9e",
        "result_path": "pa_book_structural_replication_session12_rc12_20260930.json",
        "expected_outcome": "NOT_EVALUABLE",
        "expected_reason": "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    },
    "13": {
        "raw_sha256": "3a73d4b0a8c7f4adf0917bb9ce5dc927323578c5729c455bc0a78d3c5bdb7a00",
        "result_path": "pa_book_structural_replication_session13_rc12_recheck_20260930.json",
        "expected_outcome": "REPLICATED",
        "expected_reason": "ALL_OBSERVED_TARGET_TRANSITIONS_REPLICATED",
    },
}


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_result(session_id, spec):
    path = Path(spec["result_path"])

    if not path.is_file():
        raise ValueError(
            f"missing structural replication result for session {session_id}: {path}"
        )

    payload = _load_json(path)

    if payload.get("status") != "COMPLETED":
        raise ValueError(f"session {session_id}: result status is not COMPLETED")

    if payload.get("interpretation") != "DESCRIPTIVE_ONLY":
        raise ValueError(f"session {session_id}: interpretation changed")

    if payload.get("evaluation_unit") != "formal_OPPOSED_to_ALIGNED_transition":
        raise ValueError(f"session {session_id}: evaluation unit changed")

    protocol = payload.get("protocol")
    if not isinstance(protocol, dict):
        raise ValueError(f"session {session_id}: protocol metadata missing")

    if protocol.get("sha256") != PROTOCOL_SHA256:
        raise ValueError(f"session {session_id}: protocol SHA mismatch")

    outcome = payload.get("evaluation_outcome")
    reason = payload.get("reason")

    if outcome != spec["expected_outcome"]:
        raise ValueError(
            f"session {session_id}: outcome mismatch: "
            f"{outcome!r} != {spec['expected_outcome']!r}"
        )

    if reason != spec["expected_reason"]:
        raise ValueError(
            f"session {session_id}: reason mismatch: "
            f"{reason!r} != {spec['expected_reason']!r}"
        )

    identity = payload.get("identity")
    if not isinstance(identity, dict):
        raise ValueError(f"session {session_id}: identity missing")

    if identity.get("raw_prospective_positional_identity") != "VALIDATED":
        raise ValueError(f"session {session_id}: positional identity not validated")

    safety = payload.get("safety")
    if not isinstance(safety, dict):
        raise ValueError(f"session {session_id}: safety metadata missing")

    required_false = (
        "alert_changed",
        "canonical_conflict_redefined",
        "checkpoint_extended",
        "decision_changed",
        "execution_changed",
        "operational_logic_changed",
        "post_hoc_gate_added",
        "predictive_claim_allowed",
        "rc17_changed",
        "risk_changed",
        "score_changed",
        "threshold_changed",
    )

    for key in required_false:
        if safety.get(key) is not False:
            raise ValueError(f"session {session_id}: unsafe flag {key}")

    if safety.get("research_only") is not True:
        raise ValueError(f"session {session_id}: research_only changed")

    if safety.get("descriptive_only") is not True:
        raise ValueError(f"session {session_id}: descriptive_only changed")

    transitions = payload.get("transitions")
    if not isinstance(transitions, list):
        raise ValueError(f"session {session_id}: transitions must be a list")

    return {
        "session": session_id,
        "raw_sha256": spec["raw_sha256"],
        "result_path": str(path),
        "result_sha256": _sha256(path),
        "outcome": outcome,
        "reason": reason,
        "raw_sample_count": identity.get("raw_sample_count"),
        "prospective_sample_count": identity.get("prospective_sample_count"),
        "simultaneous_directional_samples": identity.get(
            "simultaneous_directional_samples"
        ),
        "opposed_to_aligned_transition_count": identity.get(
            "opposed_to_aligned_transition_count"
        ),
        "transition_outcomes": [
            transition.get("evaluation_outcome")
            for transition in transitions
        ],
    }


def build_consolidation():
    sessions = [
        _validate_result(session_id, spec)
        for session_id, spec in EXPECTED.items()
    ]

    replicated = sum(s["outcome"] == "REPLICATED" for s in sessions)
    not_replicated = sum(s["outcome"] == "NOT_REPLICATED" for s in sessions)
    not_evaluable = sum(s["outcome"] == "NOT_EVALUABLE" for s in sessions)

    evaluable = replicated + not_replicated

    return {
        "version": VERSION,
        "status": "COMPLETED",
        "interpretation": "DESCRIPTIVE_ONLY",
        "protocol_sha256": PROTOCOL_SHA256,
        "frozen_checkpoint_extended": False,
        "independent_session_count": len(sessions),
        "evaluable_session_count": evaluable,
        "replicated_session_count": replicated,
        "not_replicated_session_count": not_replicated,
        "not_evaluable_session_count": not_evaluable,
        "sessions": sessions,
        "summary": {
            "session_11": sessions[0]["outcome"],
            "session_12": sessions[1]["outcome"],
            "session_13": sessions[2]["outcome"],
            "predictive_validation": False,
            "operational_promotion": False,
            "threshold_change_authorized": False,
            "score_change_authorized": False,
            "risk_change_authorized": False,
            "decision_change_authorized": False,
            "alert_change_authorized": False,
            "execution_change_authorized": False,
            "rc17_change_authorized": False,
            "session_14_authorized_automatically": False,
        },
    }


def main():
    output = Path(
        "pa_book_independent_replication_consolidation_sessions11_13_rc1_20260930.json"
    )

    result = build_consolidation()

    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"OUTPUT={output}")
    print(f"OUTPUT_SHA256={_sha256(output)}")


if __name__ == "__main__":
    main()
