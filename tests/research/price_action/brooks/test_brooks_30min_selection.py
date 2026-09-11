from __future__ import annotations

import tools.profit_rtd_brooks_30min_selection as runner


def test_default_window_is_exactly_30_minutes():
    assert runner.DEFAULT_CYCLES == 7200
    assert runner.DEFAULT_INTERVAL == 0.25
    assert runner.DEFAULT_DURATION_SECONDS == 1800.0


def test_runner_remains_research_only(monkeypatch, tmp_path):
    captured = {}

    def fake_run_warmed_session(symbol, **kwargs):
        captured["symbol"] = symbol
        captured.update(kwargs)
        return {
            "status": "COMPLETED",
            "symbol": symbol,
            "requested_cycles": kwargs["cycles"],
            "analyzable_samples": kwargs["cycles"],
            "skipped_cycles": 0,
            "collection_errors": 0,
            "data_ready": True,
            "output_path": None,
            "brooks_breakout_memory_capture": True,
            "brooks_first_pullback_capture": True,
            "brooks_major_reversal_context_capture": True,
            "brooks_wedge_three_pushes_capture": True,
            "brooks_trading_range_capture": True,
        }

    monkeypatch.setattr(runner, "run_warmed_session", fake_run_warmed_session)

    result = runner.run_selection("WINV26", output_dir=tmp_path, sleeper=lambda _: None)

    assert captured["symbol"] == "WINV26"
    assert captured["cycles"] == 7200
    assert captured["interval"] == 0.25
    assert result["requested_duration_seconds"] == 1800.0
    assert result["target_exact_candles_m1"] == 30
    assert result["selection_mode"] == "SELECTION"
    assert result["brooks_research_only"] is True
    assert result["brooks_predictive_claim_allowed"] is False
    assert result["brooks_score_influence_allowed"] is False
    assert result["brooks_risk_influence_allowed"] is False
    assert result["brooks_decision_influence_allowed"] is False
    assert result["brooks_alert_influence_allowed"] is False
    assert result["brooks_order_execution_allowed"] is False


def test_invalid_collection_window_is_rejected(tmp_path):
    try:
        runner.run_selection("WINV26", cycles=0, output_dir=tmp_path)
    except ValueError as exc:
        assert str(exc) == "cycles must be positive"
    else:
        raise AssertionError("expected ValueError")
