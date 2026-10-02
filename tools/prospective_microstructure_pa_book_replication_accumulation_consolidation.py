"""Descriptive consolidation of the frozen independent prospective block #14-#18."""

import hashlib
import json
from pathlib import Path

import validate_pa_book_replication_accumulation_protocol_rc1 as protocol_validator


VERSION = "RC1-PA-BOOK-INDEPENDENT-REPLICATION-ACCUMULATION-CONSOLIDATION"
SESSION_IDS = ("14", "15", "16", "17", "18")
PROTOCOL_SHA256 = "df868857d61205d9d95ff43e9259f7f8528e8feb66f0561869f20b4be78479b0"
STRUCTURAL_PROTOCOL_SHA256 = "53efb327f613934c483f6bec36ffe04bd98743b2973815f3b54ec2b84e91f01c"
OUTPUT = Path("pa_book_replication_accumulation_consolidation_sessions14_18_rc1_20261002.json")

# Exact persisted results only. Session 14 was frozen in an evaluation transcript,
# not a standalone JSON. Its full transcript is pinned, including the embedded result.
EXPECTED = {
    "14": {
        "result_file": "saida_session14_structural_replication_rc12.txt",
        "result_sha256": "0554dd676e0fbc1e167928117f981c1f56be91e29c53535e26e972cd6a73dbc1",
    },
    "15": {
        "result_file": "pa_book_structural_replication_session15_rc12_20260930.json",
        "result_sha256": "b570e2add5c6eb5a254637e5559e25fc12fae21bcc1d85f540874739a25631e1",
    },
    "16": {
        "result_file": "pa_book_structural_replication_session16_rc12_20260930.json",
        "result_sha256": "76f3fcd12b9c00082c0d489d557c99088d7f8375a2b45ba3aac5aeb4fcf7c5ce",
    },
    "17": {
        "result_file": "pa_book_structural_replication_session17_rc12_20260930.json",
        "result_sha256": "02cff1807c5d7a5bdbd506dda1b212ed4fdf13f685c0a09bee4ede5082c991f3",
    },
    "18": {
        "result_file": "pa_book_structural_replication_session18_rc12_20261002.json",
        "result_sha256": "39c7a2b70c4909240ef758a634e14f28d38c0d5d5c2f04e24d4dff8c46e346de",
    },
}
REASONS = {
    "14": "CAPTURE_INTEGRITY_FAILURE",
    "15": "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    "16": "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    "17": "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    "18": "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
}
SAFETY_FALSE = (
    "alert_changed", "canonical_conflict_redefined", "checkpoint_extended",
    "decision_changed", "execution_changed", "operational_logic_changed",
    "post_hoc_gate_added", "predictive_claim_allowed", "rc17_changed",
    "risk_changed", "score_changed", "threshold_changed",
)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _load_result(session_id, data):
    text = data.decode("utf-8-sig")
    if session_id != "14":
        return json.loads(text)
    marker = "=== STRUCTURAL EVALUATOR ===\n"
    text = text.replace("\r\n", "\n")
    _require(text.count(marker) == 1, "session 14: frozen evaluator marker missing or duplicated")
    payload, end = json.JSONDecoder().raw_decode(text.split(marker, 1)[1].lstrip())
    remainder = text.split(marker, 1)[1].lstrip()[end:]
    _require(remainder.startswith("\nEVALUATOR_EXIT_CODE=0\n"), "session 14: evaluator completion missing")
    return payload


def _validate_result(session_id, spec):
    path = Path(spec["result_file"])
    _require(path.is_file(), f"session {session_id}: missing result file: {path}")
    data = path.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    _require(actual_sha == spec["result_sha256"], f"session {session_id}: result SHA mismatch")
    payload = _load_result(session_id, data)
    _require(isinstance(payload, dict), f"session {session_id}: result must be an object")
    for key, value in {
        "status": "COMPLETED", "interpretation": "DESCRIPTIVE_ONLY",
        "evaluation_unit": "formal_OPPOSED_to_ALIGNED_transition",
        "evaluation_outcome": "NOT_EVALUABLE", "outcome": "NOT_EVALUABLE",
        "reason": REASONS[session_id],
    }.items():
        label = "outcome" if key == "evaluation_outcome" else key
        _require(payload.get(key) == value, f"session {session_id}: {label} mismatch")
    protocol = payload.get("protocol")
    _require(isinstance(protocol, dict) and protocol.get("sha256") == STRUCTURAL_PROTOCOL_SHA256,
             f"session {session_id}: structural protocol SHA mismatch")
    if "session_id" in payload:
        _require(type(payload["session_id"]) is int and payload["session_id"] == int(session_id),
                 f"session {session_id}: session identity mismatch")
    safety = payload.get("safety")
    _require(isinstance(safety, dict), f"session {session_id}: safety missing")
    for key in SAFETY_FALSE:
        _require(safety.get(key) is False, f"session {session_id}: unsafe flag {key}")
    for key in ("research_only", "descriptive_only"):
        _require(safety.get(key) is True, f"session {session_id}: unsafe flag {key}")
    transitions = payload.get("transitions")
    _require(isinstance(transitions, list) and len(transitions) == 0,
             f"session {session_id}: transition count mismatch")
    identity = payload.get("identity")
    if session_id == "14":
        # Preserve the frozen capture failure; do not require or fabricate a
        # VALIDATED identity for evidence already classified NOT_EVALUABLE.
        _require(identity is None, "session 14: frozen capture-failure identity changed")
    else:
        _require(isinstance(identity, dict), f"session {session_id}: identity missing")
        count = identity.get("opposed_to_aligned_transition_count")
        _require(type(count) is int and count == 0, f"session {session_id}: transition count mismatch")
        _require(identity.get("raw_prospective_positional_identity") == "VALIDATED",
                 f"session {session_id}: positional identity mismatch")
    return {
        "session_id": int(session_id), "result_file": str(path),
        "result_sha256": actual_sha, "outcome": payload["evaluation_outcome"],
        "reason": payload["reason"], "formal_transition_count": len(transitions),
    }


def build_consolidation():
    _require(set(EXPECTED) == set(SESSION_IDS), "missing or extra session in fixed block")
    # Reuse the full existing validator, including every frozen accumulation rule.
    _require(protocol_validator.EXPECTED_SHA256 == PROTOCOL_SHA256, "accumulation protocol SHA constant mismatch")
    validation = protocol_validator.validate()
    _require(validation["status"] == "PASS" and validation["actual_sha256"] == PROTOCOL_SHA256,
             "invalid accumulation protocol")
    protocol = json.loads(protocol_validator.PROTOCOL_PATH.read_text(encoding="utf-8-sig"))
    structural_path = Path(protocol["frozen_hypothesis"]["source_protocol"])
    _require(structural_path.is_file() and _sha256(structural_path) == STRUCTURAL_PROTOCOL_SHA256,
             "structural protocol SHA mismatch")
    sessions = [_validate_result(session_id, EXPECTED[session_id]) for session_id in SESSION_IDS]
    replicated = sum(s["outcome"] == "REPLICATED" for s in sessions)
    not_replicated = sum(s["outcome"] == "NOT_REPLICATED" for s in sessions)
    return {
        "version": VERSION, "status": "COMPLETED", "interpretation": "DESCRIPTIVE_ONLY",
        "protocol_sha256": PROTOCOL_SHA256,
        "structural_protocol_sha256": STRUCTURAL_PROTOCOL_SHA256,
        "session_ids": [int(s) for s in SESSION_IDS],
        "planned_session_count": protocol["future_block"]["planned_session_count"],
        "completed_session_count": len(sessions),
        "evaluable_session_count": replicated + not_replicated,
        "replicated_session_count": replicated, "not_replicated_session_count": not_replicated,
        "not_evaluable_session_count": sum(s["outcome"] == "NOT_EVALUABLE" for s in sessions),
        "formal_transition_count": sum(s["formal_transition_count"] for s in sessions),
        "replicated_transition_count": 0, "not_replicated_transition_count": 0,
        "sessions": sessions, "research_only": True, "predictive_claim_allowed": False,
        "causal_claim_allowed": False, "operational_change_allowed": False,
        "threshold_optimization_allowed": False, "post_hoc_admission_gate_allowed": False,
        "raw_pooling": False, "combined_session_count": None,
        "not_evaluable_is_not_failure": True, "not_evaluable_is_not_replication": True,
        "frozen_checkpoint_extended": False,
        "cohort_policy": {
            **protocol["cohort_policy"],
            "sessions_14_to_18_remain_a_separate_fixed_prospective_block": True,
        },
    }


def main():
    result = build_consolidation()
    # Refuse to replace existing evidence or artifacts.
    with OUTPUT.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"OUTPUT={OUTPUT}")
    print(f"OUTPUT_SHA256={_sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
