import copy
import json

import pytest

from tools import prospective_microstructure_pa_book_session_heterogeneity_audit as audit


def baseline(tmp_path):
    paths = []
    for i in range(10):
        pairs = [("BUY", "BUY", 0), ("BUY", "BUY", 2), ("NONE", "NONE", 0),
                 ("SELL", "BUY", 1)] if i == 0 else [("NONE", "NONE", 0)]
        value = {"samples": [{"timestamp": f"2026-09-29T00:00:0{j}", "cycle": j}
                             for j in range(len(pairs))],
                 "prospective_microstructure": {
                     "samples": [dict(price_action_bias=a, book_direction=b, conflict_count=c) for a,b,c in pairs],
                     "captured_samples": len(pairs), "source_analyzable_samples": len(pairs),
                     "sample_count_matches_source": True}}
        path = tmp_path / f"s{i}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
    return paths, audit.transition._extend_report(audit.transition.duration.build_report(paths))


def test_concentration_denominators_zero_sessions_and_ties():
    result = audit._concentration({"S1": 3, "S2": 3, "S3": 0, "S4": 2})
    assert result["total"] == 8
    assert result["shares"] == dict(S1=3/8, S2=3/8, S3=0, S4=2/8)
    assert result["top_two_share"] == 6/8
    assert result["sum_squared_shares"] == 22/64
    assert result["largest_sessions"] == ["S1", "S2"]


def test_empty_concentration_is_undefined_not_zero():
    result = audit._concentration({"S1": 0, "S2": 0})
    assert result["shares"] == {"S1": None, "S2": None}
    assert result["top_one_share"] is None
    assert result["sum_squared_shares"] is None
    assert result["largest_sessions"] == []


def test_pair_partitions_duration_and_gap_orientation(tmp_path):
    _, base = baseline(tmp_path)
    result = audit._summarize(base)
    pairs = result["pair_persistence"]
    assert pairs["BUY_BUY"]["samples"] == 2
    assert pairs["BUY_BUY"]["runs"] == 1
    assert pairs["BUY_BUY"]["total_observed_duration_seconds"] == 1
    assert pairs["BUY_BUY"]["incoming_gap"]["total_transitions"] == 0
    assert pairs["BUY_BUY"]["outgoing_gap"]["gap_seconds"]["mean"] == 2
    assert pairs["SELL_BUY"]["incoming_gap"]["total_transitions"] == 1
    assert pairs["SELL_BUY"]["outgoing_gap"]["total_transitions"] == 0
    assert pairs["SELL_SELL"]["runs"] == 0
    assert pairs["SELL_SELL"]["observed_duration_seconds"]["mean"] is None


def test_overlap_is_canonical_attribute(tmp_path):
    _, base = baseline(tmp_path)
    result = audit._summarize(base)["canonical_conflict_overlap"]
    assert result["ALIGNED"]["run_counts"] == dict(NONE=0, PARTIAL=1, FULL=0)
    assert result["ALIGNED"]["rows"][0]["conflict_sample_fraction"] == 0.5
    assert result["OPPOSED"]["run_counts"] == dict(NONE=0, PARTIAL=0, FULL=1)


def test_gap_omission_tables_do_not_change_baseline(tmp_path):
    paths, base = baseline(tmp_path)
    before = copy.deepcopy(base)
    bytes_before = [p.read_bytes() for p in paths]
    result = audit._summarize(base)
    assert base == before
    assert [p.read_bytes() for p in paths] == bytes_before
    gaps = result["transition_gaps"]
    assert len(gaps["by_session"]) == 10
    assert gaps["pooled"]["total_transitions"] == 1
    omitted = gaps["omit_one_session_descriptive_sensitivity"]
    assert omitted["FROZEN_SESSION_01"]["total_transitions"] == 0
    assert omitted["FROZEN_SESSION_02"]["total_transitions"] == 1
    assert base["session_count"] == 10


@pytest.mark.parametrize("key", ["simultaneous_directional_samples", "total_runs", "aligned_canonical_conflict_samples"])
def test_partition_mismatch_fails_closed(tmp_path, key):
    _, base = baseline(tmp_path)
    base["aggregate"][key] += 1
    with pytest.raises(ValueError, match="partition failed"):
        audit._summarize(base)


def test_safety_and_cohort_contract_inherited(tmp_path, monkeypatch):
    paths, base = baseline(tmp_path)
    entries = [(p, audit.transition.duration._sha256(p)) for p in paths]
    monkeypatch.setattr(audit.transition, "build_report", lambda: base)
    monkeypatch.setattr(audit.transition, "_frozen_entries", lambda: entries)
    result = audit.build_report()
    for k, v in audit.transition.duration.persistence._safety().items():
        assert result[k] is v
    assert result["session_count"] == 10
    assert result["cohort_redefinition"] is False
    assert result["checkpoint_extended"] is False
    assert result["unit_separation"]["transition_is_episode_claim_allowed"] is False
    assert result["descriptive_definitions"]["omission_tables_redefine_cohort"] is False


def test_input_mutation_after_summary_fails_closed(tmp_path, monkeypatch):
    paths, base = baseline(tmp_path)
    entries = [(p, audit.transition.duration._sha256(p)) for p in paths]
    monkeypatch.setattr(audit.transition, "build_report", lambda: base)
    monkeypatch.setattr(audit.transition, "_frozen_entries", lambda: entries)
    original = audit._summarize
    def mutate(value):
        result = original(value)
        paths[0].write_text("{}", encoding="utf-8")
        return result
    monkeypatch.setattr(audit, "_summarize", mutate)
    with pytest.raises(ValueError, match="mutated"):
        audit.build_report()


def test_upstream_fail_closed_is_not_suppressed(monkeypatch):
    def reject():
        raise ValueError("frozen cohort rejected")
    monkeypatch.setattr(audit.transition, "build_report", reject)
    with pytest.raises(ValueError, match="frozen cohort rejected"):
        audit.build_report()
