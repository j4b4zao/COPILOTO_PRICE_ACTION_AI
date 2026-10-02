"""Fail-closed validation of the separately frozen RC17 descriptive protocol."""
import hashlib
import json
from pathlib import Path

PROTOCOL_PATH = Path("rc17_sideways_to_directional_evolution_protocol_rc1_20261002.json")
EXPECTED_VERSION = "RC1-RC17-SIDEWAYS-TO-DIRECTIONAL-EVOLUTION-PROTOCOL"
EXPECTED_SHA256 = "2a278e7c4c438098d9ce167a778f7386a09b341a555a73e322598215150ebdb3"
EXPECTED_CONTENT_SHA256 = "9744a42b725d9754551bb1f726aee7e20cf36d4bdfc97d5b691ef571e81351c5"
VERSION = "RC1-RC17-SIDEWAYS-TO-DIRECTIONAL-EVOLUTION-PROTOCOL-VALIDATOR"


def _require(value, message):
    if not value:
        raise ValueError(message)


def validate_payload(payload):
    _require(isinstance(payload, dict), "protocol must be an object")
    _require(payload.get("version") == EXPECTED_VERSION, "protocol version mismatch")
    _require(payload.get("status") == "FROZEN_BEFORE_FUTURE_COLLECTION", "protocol not frozen")
    block = payload.get("future_block", {})
    _require(block.get("session_ids") == [19, 20, 21, 22, 23], "fixed sessions mismatch")
    _require(type(block.get("planned_session_count")) is int and block["planned_session_count"] == 5,
             "planned count mismatch")
    for field in ("fixed_before_session19", "no_auto_extension", "no_early_stop", "sessions_independent"):
        _require(block.get(field) is True, "fixed block policy mismatch: " + field)
    _require(block.get("raw_pooling_for_inference") is False, "raw pooling prohibited")
    _require(payload.get("capture_policy", {}).get("market_structure_observability_enabled") is True,
             "observability required")
    # Canonical serialization pins EVERY rule, field, exclusion, safety flag,
    # threshold-null declaration and chronology decision, including extra keys.
    # Canonical content uses LF; byte identity separately pins the file's CRLF.
    canonical = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    _require(hashlib.sha256(canonical).hexdigest() == EXPECTED_CONTENT_SHA256,
             "frozen protocol content mismatch")
    return {"status": "PASS", "validator_version": VERSION,
            "protocol_version": EXPECTED_VERSION, "protocol_sha256": EXPECTED_SHA256,
            "planned_sessions": [19, 20, 21, 22, 23], "planned_session_count": 5,
            "observability_required": True, "descriptive_only": True,
            "future_collection_executed": False}


def validate(path=PROTOCOL_PATH):
    path = Path(path)
    _require(path.is_file(), "protocol file missing")
    data = path.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == EXPECTED_SHA256, "protocol SHA256 mismatch")
    result = validate_payload(json.loads(data.decode("utf-8")))
    return {**result, "protocol_file": str(path), "protocol_status": "FROZEN_BEFORE_FUTURE_COLLECTION"}


def main():
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
