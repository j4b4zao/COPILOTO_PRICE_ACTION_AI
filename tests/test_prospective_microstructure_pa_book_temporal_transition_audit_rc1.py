from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta

import pytest

from tools import prospective_microstructure_pa_book_temporal_transition_audit as audit


def sample(pair=None, conflict=0):
    pa, book = pair.split("_") if pair else ("NONE", "NONE")
    return dict(price_action_bias=pa, book_direction=book, conflict_count=conflict)


def payload(pairs):
    samples = [sample(p) for p in pairs]
    return {
        "samples": [{"timestamp": (datetime(2026, 9, 29) + timedelta(seconds=i * 2.5)).isoformat(),
                     "cycle": i + 1} for i in range(len(samples))],
        "prospective_microstructure": {
            "samples": samples, "captured_samples": len(samples),
            "source_analyzable_samples": len(samples), "sample_count_matches_source": True},
    }


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def session(tmp_path, pairs):
    path = write(tmp_path / "session.json", payload(pairs))
    return audit.duration._audit_session("S1", path)


@pytest.mark.parametrize("pairs,count", [([], 0), ([None], 0), (["BUY_BUY"], 0),
    (["BUY_BUY", None, "BUY_SELL", "SELL_SELL"], 2)])
def test_n_runs_minus_one(tmp_path, pairs, count):
    result = session(tmp_path, pairs)
    assert len(audit._transitions(result)) == count == max(len(result["runs"]) - 1, 0)


@pytest.mark.parametrize("previous,following,relation", [
    ("BUY_BUY", "SELL_SELL", "ALIGNED->ALIGNED"),
    ("BUY_BUY", "BUY_SELL", "ALIGNED->OPPOSED"),
    ("BUY_SELL", "SELL_SELL", "OPPOSED->ALIGNED"),
    ("BUY_SELL", "SELL_BUY", "OPPOSED->OPPOSED"),
])
def test_relation_and_exact_pair_changes(tmp_path, previous, following, relation):
    rows = audit._transitions(session(tmp_path, [previous, following]))
    assert len(rows) == 1
    row = rows[0]
    assert row["previous_pair"] == previous
    assert row["next_pair"] == following
    assert row["previous_relation"] + "->" + row["next_relation"] == relation
    assert row["gap_samples"] == 0
    assert row["gap_seconds"] == 2.5
    assert row["previous_run"] == 1 and row["next_run"] == 2


def test_gap_excludes_endpoints_and_uses_actual_timestamps(tmp_path):
    value = payload(["BUY_BUY", "BUY_BUY", None, None, "BUY_BUY"])
    value["samples"][-1]["timestamp"] = "2026-09-29T00:01:00"
    result = audit.duration._audit_session("S1", write(tmp_path / "s.json", value))
    row, = audit._transitions(result)
    assert (row["previous_end_index"], row["next_start_index"]) == (1, 4)
    assert row["gap_samples"] == 2
    assert row["gap_seconds"] == 57.5


def synthetic_report(tmp_path, pairs):
    paths = [write(tmp_path / f"s{i}.json", payload(pairs)) for i in range(10)]
    return paths, audit.duration.build_report(paths)


def test_no_cross_session_transitions_and_no_mutation(tmp_path):
    paths, base = synthetic_report(tmp_path, ["BUY_BUY", "BUY_SELL"])
    before = copy.deepcopy(base)
    files = [p.read_bytes() for p in paths]
    report = audit._extend_report(base)
    assert base == before
    assert files == [p.read_bytes() for p in paths]
    assert report["aggregate"]["total_transitions"] == 10
    for s in report["sessions"]:
        assert len(s["transitions"]) == 1
        assert s["transitions"][0]["session"] == s["label"]
    _, singleton = synthetic_report(tmp_path, ["BUY_BUY"])
    assert audit._extend_report(singleton)["aggregate"]["total_transitions"] == 0


@pytest.mark.parametrize("case", ["timestamp", "timestamp_regression", "cycle", "cycle_regression",
    "metadata", "metadata_bool", "count", "conflict", "direction", "timezone"])
def test_invalid_inputs_fail_closed(tmp_path, case):
    value = payload(["BUY_BUY", "BUY_SELL"])
    raw, meta = value["samples"], value["prospective_microstructure"]
    if case == "timestamp":
        raw[0]["timestamp"] = "invalid"
    elif case == "timestamp_regression":
        raw.reverse()
    elif case == "cycle":
        raw[0]["cycle"] = True
    elif case == "cycle_regression":
        raw[1]["cycle"] = 0
    elif case == "metadata":
        meta["sample_count_matches_source"] = False
    elif case == "metadata_bool":
        meta["captured_samples"] = True
    elif case == "count":
        raw.pop()
    elif case == "conflict":
        del meta["samples"][0]["conflict_count"]
    elif case == "direction":
        meta["samples"][0]["book_direction"] = "INVALID"
    else:
        raw[1]["timestamp"] += "+00:00"
    with pytest.raises((ValueError, TypeError)):
        audit.duration._audit_session("S1", write(tmp_path / "bad.json", value))


def test_conflict_is_attribute_not_run_or_transition_definition(tmp_path):
    value = payload(["BUY_BUY", "BUY_BUY", None, "BUY_SELL", "BUY_SELL"])
    value["prospective_microstructure"]["samples"][0]["conflict_count"] = 4
    path = write(tmp_path / "s.json", value)
    row, = audit._transitions(audit.duration._audit_session("S", path))
    assert row["previous_canonical_conflict_samples"] == 1
    assert row["next_canonical_conflict_samples"] == 0
    assert (row["previous_end_index"], row["next_start_index"]) == (1, 3)


def bind_synthetic(tmp_path, monkeypatch):
    paths, base = synthetic_report(tmp_path, ["BUY_BUY", None, "BUY_SELL"])
    entries = [(p, audit.duration._sha256(p)) for p in paths]
    monkeypatch.setattr(audit, "_frozen_entries", lambda: entries)
    monkeypatch.setattr(audit, "EXPECTED_BASELINE", {k: base["aggregate"][k] for k in audit.EXPECTED_BASELINE})
    return paths


@pytest.mark.parametrize("count", [0, 9, 11, 12])
def test_exactly_ten_sessions(tmp_path, monkeypatch, count):
    paths = bind_synthetic(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="exactly 10"):
        audit.build_report((paths + paths)[:count])


def test_duplicate_path_fails_closed(tmp_path, monkeypatch):
    paths = bind_synthetic(tmp_path, monkeypatch)
    paths[-1] = paths[0]
    with pytest.raises(ValueError, match="distinct"):
        audit.build_report(paths)


@pytest.mark.parametrize("case", ["reorder", "replace", "hash", "numeric"])
def test_frozen_identity_fail_closed(tmp_path, monkeypatch, case):
    paths = bind_synthetic(tmp_path, monkeypatch)
    if case == "reorder":
        paths.reverse()
    elif case == "replace":
        paths[-1] = write(tmp_path / "session11.json", payload(["BUY_BUY"]))
    elif case == "hash":
        paths[0].write_text("{}", encoding="utf-8")
    else:
        monkeypatch.setattr(audit, "EXPECTED_BASELINE", {"samples": 99999})
    with pytest.raises(ValueError, match="frozen"):
        audit.build_report(paths)


def test_manifest_tampering_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "MANIFEST", write(tmp_path / "manifest.json", {"session_count": 12}))
    with pytest.raises(ValueError, match="manifest identity"):
        audit.build_report()


def test_mutation_during_transition_audit_fails_closed(tmp_path, monkeypatch):
    paths = bind_synthetic(tmp_path, monkeypatch)
    original = audit._extend_report
    def mutate(base):
        result = original(base)
        paths[0].write_text("{}", encoding="utf-8")
        return result
    monkeypatch.setattr(audit, "_extend_report", mutate)
    with pytest.raises(ValueError, match="mutated"):
        audit.build_report(paths)


def test_full_contract_and_input_preservation(tmp_path, monkeypatch):
    paths = bind_synthetic(tmp_path, monkeypatch)
    before = [p.read_bytes() for p in paths]
    report = audit.build_report(paths)
    assert before == [p.read_bytes() for p in paths]
    for flag in ("research_only", "observational_only", "descriptive_only"):
        assert report[flag] is True
    for flag in ("predictive_claim_allowed", "score_influence_allowed", "risk_influence_allowed",
                 "decision_influence_allowed", "alert_influence_allowed", "order_execution_allowed",
                 "promotion_allowed", "threshold_change_allowed", "rc17_change_allowed",
                 "order_flow_score_change_allowed", "threshold_changed", "rc17_changed",
                 "operational_logic_changed", "canonical_conflict_redefinition", "checkpoint_extended",
                 "independent_sessions_appended", "combined_checkpoint_created", "cohort_redefinition"):
        assert report[flag] is False
    assert report["combined_session_count"] is None
    assert report["session_count"] == report["frozen_checkpoint_session_count"] == 10
    assert report["unit_separation"]["frozen_opposed_episode_count"] == 17
    for unit in ("run", "sample", "episode"):
        assert report["unit_separation"][f"transition_is_{unit}_claim_allowed"] is False


def test_group_summaries_include_absent_pairs_and_concentration(tmp_path):
    _, base = synthetic_report(tmp_path, ["BUY_BUY", None, "BUY_BUY"])
    aggregate = audit._extend_report(base)["aggregate"]
    assert len(aggregate["pair_transitions"]) == 16
    same = aggregate["relation_transitions"]["ALIGNED->ALIGNED"]
    assert same["total_transitions"] == 10
    assert same["largest_session_share"] == 0.1
    assert same["gap_seconds"] == dict(count=10, min=5.0, median=5.0, mean=5.0, max=5.0)
    absent = aggregate["pair_transitions"]["SELL_SELL->SELL_SELL"]
    assert absent["total_transitions"] == 0
    assert absent["largest_session_share"] is None
    assert absent["gap_seconds"]["median"] is None
