import json
from types import SimpleNamespace

import tools.profit_rtd_microstructure_prospective_session as runner
from analysis.replay.microstructure_confluence_replay_recorder import (
    MicrostructureConfluenceReplayRecorder,
)


def _context():
    return SimpleNamespace(
        price_action=SimpleNamespace(bias="BUY"),
        order_flow=SimpleNamespace(
            pressure="BUY",
            flow_momentum="PERSISTENT_BUY",
            pattern_direction="BUY",
            structure_alignment="ALIGNED",
            structural_pattern_confidence=0.8,
        ),
        book_depth_analysis=SimpleNamespace(
            valid=True,
            pressure="BID_DOMINANT",
            concentration_bias="BID_DOMINANT",
            confidence=0.8,
            duplicate_evidence_risk=False,
        ),
    )


def test_warmup_samples_are_excluded_and_main_window_is_persisted(tmp_path, monkeypatch):
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.record(_context())
    pipeline = SimpleNamespace(microstructure_confluence_replay=recorder)
    output = tmp_path / "session.json"

    def fake_warm_history(*args, **kwargs):
        return {"ready": True, "pipeline": pipeline}

    def fake_run(symbol, **kwargs):
        assert kwargs["require_trade_context_at_start"] is True
        warm = runner.base.warm_history(symbol)
        assert warm["ready"] is True
        assert recorder.size == 0
        recorder.record(_context())
        recorder.record(_context())
        payload = {
            "status": "COMPLETED",
            "data_ready": True,
            "analyzable_samples": 2,
        }
        output.write_text(json.dumps(payload), encoding="utf-8")
        return {**payload, "output_path": str(output)}

    original = runner.base.warm_history
    monkeypatch.setattr(runner.base, "warm_history", fake_warm_history)
    monkeypatch.setattr(runner.base, "run_warmed_session", fake_run)

    result = runner.run_session(
        "WINV26",
        cycles=2,
        interval=0,
        require_trade_context_at_start=True,
    )

    evidence = result["prospective_microstructure"]
    assert evidence["captured_samples"] == 2
    assert evidence["sample_count_matches_source"] is True
    assert evidence["samples"][0]["flow_momentum"] == "PERSISTENT_BUY"
    assert evidence["samples"][0]["book_pressure"] == "BID_DOMINANT"
    assert evidence["observational_only"] is True
    assert evidence["order_execution_allowed"] is False
    assert runner.base.warm_history is fake_warm_history
    assert original is not runner.base.warm_history

    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["prospective_microstructure"]["captured_samples"] == 2
    assert persisted["score_influence_allowed"] is False
    assert persisted["risk_influence_allowed"] is False
    assert persisted["decision_influence_allowed"] is False
    assert persisted["alert_influence_allowed"] is False
    assert persisted["order_execution_allowed"] is False


def test_base_warm_history_is_restored_after_failure(monkeypatch):
    original = runner.base.warm_history

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(runner.base, "run_warmed_session", fail)

    try:
        runner.run_session("WINV26", cycles=1, interval=0)
    except RuntimeError:
        pass
    else:
        raise AssertionError("RuntimeError expected")

    assert runner.base.warm_history is original


def test_missing_pipeline_fails_closed_without_evidence(monkeypatch):
    def fake_run(symbol, **kwargs):
        return {
            "status": "ABORTED_CONTEXT_NOT_READY",
            "data_ready": False,
            "analyzable_samples": 0,
        }

    monkeypatch.setattr(runner.base, "run_warmed_session", fake_run)

    result = runner.run_session("WINV26", cycles=1, interval=0)
    evidence = result["prospective_microstructure"]

    assert evidence["captured_samples"] == 0
    assert evidence["sample_count_matches_source"] is True
    assert evidence["samples"] == []
    assert evidence["promotion_allowed"] is False
