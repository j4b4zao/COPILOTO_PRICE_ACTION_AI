import tools.profit_rtd_brooks_management_outcome_research as mod


def _sample(cid, high, low, close=100.0):
    return {
        "candle_evidence": {
            "candle_id": cid,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
        }
    }


def _episode():
    return {
        "episode_id": "C1|BUY",
        "entry_event_candle_id": "C1",
        "entry_exact_index": 0,
        "direction": "BUY",
        "entry_price": 100.0,
        "initial_stop": 95.0,
        "current_stop": 99.0,
        "stop_revision_count": 1,
        "observations": [
            {
                "observation_exact_index": 1,
                "revision_applied": True,
                "current_stop_after": 99.0,
            }
        ],
    }


def test_trailing_revision_only_applies_next_candle():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 104, 98),
        _sample("C3", 103, 98.5),
    ]
    idx = mod._index_exact_samples(exact)

    report = mod.analyze_episode(_episode(), exact, idx)

    assert report["trailing_stop_hit"] is True
    assert report["trailing_exit_candle_id"] == "C3"
    assert report["trailing_exit_stop"] == 99.0
    assert report["trailing_exit_protected_r"] == -0.2


def test_initial_stop_baseline_can_survive_while_trailing_exits():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 104, 98),
        _sample("C3", 103, 98.5),
    ]
    idx = mod._index_exact_samples(exact)

    report = mod.analyze_episode(_episode(), exact, idx)

    assert report["baseline_initial_stop_hit"] is False
    assert report["trailing_stop_hit"] is True


def test_mfe_mae_are_measured_in_initial_r():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 110, 97),
    ]
    idx = mod._index_exact_samples(exact)

    report = mod.analyze_episode(_episode(), exact, idx)

    assert report["mfe_r"] == 2.0
    assert report["mae_r"] == 0.6


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
