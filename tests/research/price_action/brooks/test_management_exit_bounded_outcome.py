import tools.profit_rtd_brooks_management_exit_bounded_outcome as mod


def _sample(cid, high, low, close=100.0):
    return {
        "candle_evidence": {
            "candle_id": cid,
            "high": high,
            "low": low,
            "close": close,
        }
    }


def _episode(observations=None):
    return {
        "episode_id": "C1|BUY",
        "entry_event_candle_id": "C1",
        "direction": "BUY",
        "entry_price": 100.0,
        "initial_stop": 95.0,
        "observations": observations or [],
    }


def test_baseline_mae_stops_at_initial_stop_candle():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 104, 94),
        _sample("C3", 110, 80),
    ]

    result = mod.analyze_episode(_episode(), exact)

    assert result["baseline"]["exit_type"] == "INITIAL_STOP"
    assert result["baseline"]["exit_candle_id"] == "C2"
    assert result["baseline"]["mae_r"] == 1.2
    # C3 nao pode contaminar a excursao apos a saida.
    assert result["baseline"]["mfe_r"] == 0.8


def test_trailing_revision_applies_only_next_candle():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 104, 98),
        _sample("C3", 103, 98.5),
    ]
    episode = _episode([
        {
            "observation_exact_index": 1,
            "revision_applied": True,
            "current_stop_after": 99.0,
        }
    ])

    result = mod.analyze_episode(episode, exact)

    assert result["trailing"]["exit_type"] == "TRAILING_STOP"
    assert result["trailing"]["exit_candle_id"] == "C3"
    assert result["trailing"]["exit_stop"] == 99.0
    assert result["trailing"]["exit_r"] == -0.2


def test_censored_episode_is_not_fabricated_as_realized_exit():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 104, 98, close=103),
    ]

    result = mod.analyze_episode(_episode(), exact)

    assert result["baseline"]["exit_type"] == "SESSION_END_CENSORED"
    assert result["baseline"]["exit_r"] is None
    assert result["baseline"]["session_end_mark_r"] == 0.6


def test_sell_stop_geometry_and_exit_r():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 106, 98),
    ]
    episode = {
        "episode_id": "C1|SELL",
        "entry_event_candle_id": "C1",
        "direction": "SELL",
        "entry_price": 100.0,
        "initial_stop": 105.0,
        "observations": [],
    }

    result = mod.analyze_episode(episode, exact)

    assert result["baseline"]["exit_type"] == "INITIAL_STOP"
    assert result["baseline"]["exit_r"] == -1.0


def test_safety_contract_remains_research_only():
    report = mod.analyze_many({"sessions": []})

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["predictive_claim_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["performance_claim_allowed"] is False
    assert report["hypothesis_freeze_allowed"] is False
    assert report["dynamic_management_validated"] is False
    assert report["performance_validated"] is False
