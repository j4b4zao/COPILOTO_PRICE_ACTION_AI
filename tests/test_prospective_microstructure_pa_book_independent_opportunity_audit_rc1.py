import json
from pathlib import Path
import pytest
from tools import prospective_microstructure_pa_book_independent_opportunity_audit as audit


def payload():
    samples = [{"price_action_bias": p, "book_direction": b} for p in ("BUY", "SELL", "NONE") for b in ("BUY", "SELL", "NONE")]
    return {"samples": [{"timestamp": f"2026-10-02T09:00:0{i}", "cycle": i} for i in range(9)],
            "prospective_microstructure": {"samples": samples, "captured_samples": 9,
                "source_analyzable_samples": 9, "sample_count_matches_source": True}}


def test_explicit_sessions_and_no_discovery(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("discovery forbidden")
    monkeypatch.setattr(Path, "glob", forbidden)
    monkeypatch.setattr(Path, "rglob", forbidden)
    assert list(audit.SESSIONS) == [11,12,13,14,15,16,17,18]
    assert [r["session_id"] for r in audit.build_report()["sessions"]] == list(audit.SESSIONS)


def test_session14_null_and_never_parsed(monkeypatch):
    monkeypatch.setattr(audit, "count_payload", lambda p: pytest.fail("must not parse #14"))
    row = audit.audit_session(14, audit.SESSIONS[14], audit.RAW_SHA256[14])
    assert row["SESSION_OPPORTUNITY_STATUS"] == "NOT_AVAILABLE_CAPTURE_INTEGRITY_FAILURE"
    assert all(v is None for v in row["counts"].values())


def test_all_pairs_and_identities():
    c, identities = audit.count_payload(payload())
    assert all(identities.values())
    assert c["TOTAL_PROSPECTIVE_SAMPLES"] == 9
    assert c["BOTH_DIRECTIONAL"] == 4
    assert c["ALIGNED"] == c["OPPOSED"] == 2
    assert c["BOTH_NONE"] == 1
    assert c["PA_DIRECTIONAL_BOOK_NONE"] == c["PA_NONE_BOOK_DIRECTIONAL"] == 2
    assert c["PA_BUY"] == c["PA_SELL"] == c["PA_NONE"] == 3


@pytest.mark.parametrize("field", ["TOTAL_PROSPECTIVE_SAMPLES", "BUY_BUY", "ALIGNED", "OPPOSED", "BOTH_DIRECTIONAL"])
def test_identity_failure_closed(field):
    c, _ = audit.count_payload(payload())
    c[field] += 1
    with pytest.raises(ValueError, match="identity failure"):
        audit.validate_identities(c)


@pytest.mark.parametrize("kind", ["missing_prospective", "missing_formal", "invalid_direction", "positional", "capture"])
def test_invalid_capture_has_null_counts(tmp_path, kind):
    p = payload()
    if kind == "missing_prospective": del p["prospective_microstructure"]
    elif kind == "missing_formal": del p["prospective_microstructure"]["samples"][0]["book_direction"]
    elif kind == "invalid_direction": p["prospective_microstructure"]["samples"][0]["price_action_bias"] = "UNKNOWN"
    elif kind == "positional": p["samples"][1]["cycle"] = -1
    else: p["prospective_microstructure"]["captured_samples"] = 10
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(p), encoding="utf-8")
    row = audit.audit_session(11, path, audit.reference._sha256(path))
    assert row["SESSION_OPPORTUNITY_STATUS"] == "NOT_AVAILABLE_CAPTURE_INTEGRITY_FAILURE"
    assert all(v is None for v in row["counts"].values())


def test_real_aggregate_is_valid_sessions_only():
    r = audit.build_report()
    valid = [s for s in r["sessions"] if s["SESSION_OPPORTUNITY_STATUS"] == "VALID_COUNTS"]
    assert len(valid) == r["aggregate"]["VALID_COUNT_SESSION_COUNT"] == 7
    assert r["aggregate"]["TOTAL_VALID_PROSPECTIVE_SAMPLES"] == sum(s["counts"]["TOTAL_PROSPECTIVE_SAMPLES"] for s in valid)


def test_no_reclassification_threshold_or_operational_changes():
    r = audit.build_report()
    assert r["outcomes_reclassified"] is False
    assert r["diagnostic_only"] is True
    for k in ("threshold_changed", "rc17_changed", "operational_logic_changed", "predictive_claim_allowed", "threshold_change_allowed"):
        assert r[k] is False
    assert all("outcome" not in session and "evaluation_outcome" not in session for session in r["sessions"])
    assert "recommendation" not in json.dumps(r)


def test_checkpoint_and_cohorts_unchanged():
    r = audit.build_report()
    assert r["checkpoint_extended"] is False
    assert r["combined_session_count"] is None
    assert r["raw_pooling_for_inference"] is False
    assert all(r["cohort_policy"].values())


def test_sha_mismatch_closed(tmp_path):
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")
    assert audit.audit_session(11, path, "bad")["counts"]["TOTAL_PROSPECTIVE_SAMPLES"] is None
