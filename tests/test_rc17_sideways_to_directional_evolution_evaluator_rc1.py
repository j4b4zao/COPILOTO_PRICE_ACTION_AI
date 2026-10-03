"""Synthetic evidence lives exclusively in pytest temporary directories."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from tools import rc17_sideways_to_directional_evolution_evaluator as evaluator

PROTOCOL = Path("rc17_sideways_to_directional_evolution_protocol_rc1_20261002.json")


def sample(trend, cycle=1):
    flags = {k: (trend == "UP" if k in ("hh", "hl") else trend == "DOWN") for k in evaluator.FLAGS}
    structure = {"trend": trend, "valid": True, **flags, "bos_up": False,
                 "bos_down": False, "choch": False, "last_high": 0.0, "last_low": 0.0}
    closed = [{"index": i, "timestamp": f"2026-10-03T09:0{i}:00",
               "open": 5, "high": 10, "low": 1, "close": 5, "volume": 1} for i in range(5)]
    observed = {k: structure[k] for k in ("trend", "valid", "bos_up", "bos_down", "choch", "last_high", "last_low")}
    observed.update({name: flags[k] for k, name in evaluator.FLAGS.items()})
    d = {"engine_version": "RC17-CLOSED-CANDLE", "guard_status": "EXECUTED",
         "history_unchanged_during_pipeline": True, "symbol": "SYNTHETIC_ONLY",
         "cycle": cycle, "timestamp": f"2026-10-03T10:00:{cycle:02d}",
         "closed_candles": closed, "closed_candle_count": 5, "total_candle_count": 6,
         "closed_history_sha256": hashlib.sha256(evaluator._canonical(closed)).hexdigest(),
         "excluded_forming_candle": {**closed[-1], "index": 5, "timestamp": "2026-10-03T09:05:00"},
         "observed_result": observed}
    for kind in ("high", "low"):
        d.update({"swing_" + kind + "s": [], "swing_" + kind + "_count": 0,
                  "latest_swing_" + kind: None, "previous_swing_" + kind: None})
    return {"cycle": cycle, "timestamp": d["timestamp"], "structure": structure,
            "price_action": {"bias": {"UP": "BUY", "DOWN": "SELL"}.get(trend, "NONE")},
            "market_structure_observability": d}


def run(tmp_path, samples, **kwargs):
    raw = {"symbol": "SYNTHETIC_ONLY", "samples": samples, "requested_cycles": len(samples),
           "analyzable_samples": len(samples), "skipped_cycles": 0, "collection_errors": 0}
    path = tmp_path / "synthetic_fixture.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    before = path.read_bytes()
    result = evaluator.evaluate(path, kwargs.pop("session_id", 23), kwargs.pop("protocol_path", PROTOCOL), **kwargs)
    assert path.read_bytes() == before
    return result


@pytest.mark.parametrize("a,b,events", [("SIDEWAYS", "SIDEWAYS", 0), ("SIDEWAYS", "UP", 1),
    ("SIDEWAYS", "DOWN", 1), ("UP", "SIDEWAYS", 0), ("DOWN", "UP", 0), ("UNKNOWN", "UP", 0)])
def test_transitions(tmp_path, a, b, events):
    r = run(tmp_path, [sample(a), sample(b, 2)])
    assert r["integrity"]["valid"]
    assert r["primary_event_count"] == events
    assert r["session_classification"] == ("DIRECTIONAL_TRANSITION_OBSERVED" if events else "NO_DIRECTIONAL_TRANSITION_OBSERVED")
    counts = r["unknown_transition_counts"] if a == "UNKNOWN" else r["transition_counts"]
    assert counts[a + "_TO_" + b] == 1
    if events:
        assert r["primary_events"][0]["before"]["latest_swing_high"] is None
        assert r["primary_events"][0]["after"]["trend"] == b


@pytest.mark.parametrize("mutation", [
    lambda s: s.pop("market_structure_observability"),
    lambda s: s["market_structure_observability"].update(history_unchanged_during_pipeline=False),
    lambda s: s["market_structure_observability"].pop("closed_history_sha256"),
    lambda s: s["market_structure_observability"].update(closed_history_sha256="bad"),
    lambda s: s["market_structure_observability"].update(closed_history_sha256="a" * 64),
    lambda s: s["market_structure_observability"].update(swing_high_count=1),
    lambda s: s["market_structure_observability"].update(closed_candle_count=4),
    lambda s: s["market_structure_observability"].update(latest_swing_low={"price": 1}),
    lambda s: s["market_structure_observability"].update(guard_status="DIAGNOSTIC_UNAVAILABLE"),
    lambda s: s["market_structure_observability"]["observed_result"].update(trend="DOWN"),
    lambda s: s["market_structure_observability"]["observed_result"].update(higher_high=True),
    lambda s: s["market_structure_observability"]["excluded_forming_candle"].update(index=0),
    lambda s: s["market_structure_observability"]["closed_candles"][0].update(index=1),
])
def test_integrity_failures_no_reconstruction(tmp_path, mutation):
    bad = sample("SIDEWAYS", 2)
    mutation(bad)
    original = copy.deepcopy(bad)
    r = run(tmp_path, [sample("SIDEWAYS"), bad, sample("UP", 3)])
    assert r["session_classification"] == "CAPTURE_INTEGRITY_FAILURE"
    assert r["primary_event_count"] == 0
    assert bad == original


@pytest.mark.parametrize("trend,flag", [("UP", "hh"), ("UP", "hl"), ("DOWN", "lh"), ("DOWN", "ll")])
def test_directional_flags_required(tmp_path, trend, flag):
    s = sample(trend)
    s["structure"][flag] = False
    s["market_structure_observability"]["observed_result"][evaluator.FLAGS[flag]] = False
    assert run(tmp_path, [s])["session_classification"] == "CAPTURE_INTEGRITY_FAILURE"


@pytest.mark.parametrize("session_id", [18, 24, True, "19"])
def test_session_boundary(tmp_path, session_id):
    with pytest.raises(ValueError, match="session_id"):
        run(tmp_path, [sample("SIDEWAYS")], session_id=session_id)


def test_protocol_hash_fail_closed(tmp_path):
    protocol = tmp_path / "altered_protocol.json"
    protocol.write_bytes(PROTOCOL.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SHA256"):
        run(tmp_path, [sample("SIDEWAYS")], protocol_path=protocol)


def test_raw_immutability_and_output(tmp_path):
    r = run(tmp_path, [sample("SIDEWAYS")], output_path=tmp_path / "evaluation.json")
    assert r["integrity"]["raw_sha_before"] == r["integrity"]["raw_sha_after"] == r["raw"]["sha256"]
    assert json.loads((tmp_path / "evaluation.json").read_text()) == r


@pytest.mark.parametrize("protected", ["raw", "protocol", "hardlink"])
def test_output_cannot_overwrite_inputs(tmp_path, protected):
    run(tmp_path, [sample("SIDEWAYS")])
    raw = tmp_path / "synthetic_fixture.json"
    target = raw if protected == "raw" else PROTOCOL
    if protected == "hardlink":
        target = tmp_path / "alias.json"
        target.hardlink_to(raw)
    with pytest.raises(ValueError, match="overwrite"):
        evaluator.evaluate(raw, 23, PROTOCOL, target)


def test_invalid_predecessor_not_eligible(tmp_path):
    s = sample("SIDEWAYS")
    s["structure"]["valid"] = False
    s["market_structure_observability"]["observed_result"]["valid"] = False
    assert run(tmp_path, [s, sample("UP", 2)])["primary_event_count"] == 0


def test_skipped_cycles_not_imputed(tmp_path):
    raw = {"symbol": "SYNTHETIC_ONLY", "samples": [sample("SIDEWAYS"), sample("UP", 3)],
           "requested_cycles": 3, "analyzable_samples": 2, "skipped_cycles": 1, "collection_errors": 0}
    path = tmp_path / "synthetic_fixture.json"
    path.write_text(json.dumps(raw))
    r = evaluator.evaluate(path, 23, PROTOCOL)
    assert r["primary_event_count"] == 1
    assert sum(r["transition_counts"].values()) == 1


def test_raw_mutation_detected(tmp_path, monkeypatch):
    run(tmp_path, [sample("SIDEWAYS")])
    raw = tmp_path / "synthetic_fixture.json"
    original = Path.read_bytes
    calls = 0
    def changed(path):
        nonlocal calls
        data = original(path)
        if path == raw:
            calls += 1
            if calls == 2:
                return data + b" "
        return data
    monkeypatch.setattr(Path, "read_bytes", changed)
    r = evaluator.evaluate(raw, 23, PROTOCOL)
    assert r["session_classification"] == "CAPTURE_INTEGRITY_FAILURE"
    assert not r["integrity"]["raw_unchanged"]


@pytest.mark.parametrize("high,low,key", [(True, False, "SAMPLES_WITH_HIGH_ONLY"),
    (False, True, "SAMPLES_WITH_LOW_ONLY"), (True, True, "SAMPLES_WITH_BOTH_SWING_TYPES"),
    (False, False, "SAMPLES_WITH_NO_SWINGS")])
def test_swing_states(tmp_path, high, low, key):
    s = sample("SIDEWAYS")
    d = s["market_structure_observability"]
    for kind, present in (("high", high), ("low", low)):
        if present:
            swing = {"history_index": 2, "timestamp": d["closed_candles"][2]["timestamp"],
                     "price": d["closed_candles"][2][kind]}
            d["swing_" + kind + "s"] = [swing]
            d["swing_" + kind + "_count"] = 1
            d["latest_swing_" + kind] = copy.deepcopy(swing)
    r = run(tmp_path, [s])
    assert r["integrity"]["valid"]
    assert r["swing_state_counts"][key] == 1


@pytest.mark.parametrize("mutation", [lambda s: s.update(cycle=1),
    lambda s: s.update(timestamp="2026-10-03T08:00:00"), lambda s: s.pop("timestamp")])
def test_chronology_fail_closed(tmp_path, mutation):
    bad = sample("SIDEWAYS", 2)
    mutation(bad)
    r = run(tmp_path, [sample("SIDEWAYS"), bad, sample("UP", 3)])
    assert r["session_classification"] == "CAPTURE_INTEGRITY_FAILURE"
    assert r["primary_event_count"] == 0


@pytest.mark.parametrize("session_id", [19, 20, 21, 22, 23])
def test_all_allowed_session_labels(tmp_path, session_id):
    # These are evaluator labels on temporary SYNTHETIC_ONLY fixtures, never captures.
    assert run(tmp_path, [sample("SIDEWAYS")], session_id=session_id)["session_id"] == session_id


def test_offline_module_has_no_operational_dependencies():
    import ast
    tree = ast.parse(Path(evaluator.__file__).read_text())
    modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert all(not (name or "").startswith(("analysis", "market_data", "connectors")) for name in modules)


@pytest.mark.parametrize("bad", [None, [], {"structure": None},
    {"structure": {"trend": []}, "price_action": {"bias": []}}])
def test_malformed_samples_classified(tmp_path, bad):
    assert run(tmp_path, [bad])["session_classification"] == "CAPTURE_INTEGRITY_FAILURE"
