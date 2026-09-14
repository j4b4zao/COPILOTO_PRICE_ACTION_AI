import tools.profit_rtd_brooks_management_intrabar_bounded_outcome as mod


def _sample(cid, high, low, close=100.0):
    return {
        "candle_evidence": {
            "candle_id": cid,
            "high": high,
            "low": low,
            "close": close,
        }
    }


def _episode(direction="BUY", observations=None):
    if direction == "BUY":
        entry = 100.0
        stop = 95.0
    else:
        entry = 100.0
        stop = 105.0

    return {
        "episode_id": f"C1|{direction}",
        "entry_event_candle_id": "C1",
        "direction": direction,
        "entry_price": entry,
        "initial_stop": stop,
        "observations": observations or [],
    }


def test_no_post_entry_evidence_is_explicit():
    result = mod.analyze_episode(
        _episode(),
        [_sample("C1", 101, 99)],
    )

    assert result["status"] == "NO_POST_ENTRY_EVIDENCE"
    assert result["baseline"]["status"] == "NO_POST_ENTRY_EVIDENCE"
    assert result["trailing"]["status"] == "NO_POST_ENTRY_EVIDENCE"


def test_baseline_mae_is_bounded_at_one_r_on_stop_candle():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 110, 90),
    ]

    result = mod.analyze_episode(_episode(), exact)

    assert result["baseline"]["exit_type"] == "INITIAL_STOP"
    assert result["baseline"]["bounded_mae_r"] == 1.0


def test_exit_candle_mfe_is_possible_not_confirmed():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 110, 94),
    ]

    result = mod.analyze_episode(_episode(), exact)

    assert result["baseline"]["confirmed_mfe_r"] == 0.0
    assert result["baseline"]["possible_mfe_r"] == 2.0
    assert result["baseline"]["exit_candle_intrabar_ambiguous"] is True


def test_confirmed_mfe_uses_pre_exit_candles():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 105, 98),
        _sample("C3", 110, 94),
    ]

    result = mod.analyze_episode(_episode(), exact)

    assert result["baseline"]["confirmed_mfe_r"] == 1.0
    assert result["baseline"]["possible_mfe_r"] == 2.0


def test_trailing_mae_is_bounded_by_active_tighter_stop():
    exact = [
        _sample("C1", 101, 99),
        _sample("C2", 104, 98),
        _sample("C3", 108, 98.5),
    ]
    episode = _episode(observations=[
        {
            "observation_exact_index": 1,
            "revision_applied": True,
            "current_stop_after": 99.0,
        }
    ])

    result = mod.analyze_episode(episode, exact)

    assert result["trailing"]["exit_type"] == "TRAILING_STOP"
    assert result["trailing"]["exit_r"] == -0.2
    assert result["trailing"]["bounded_mae_r"] == 0.4


def test_safety_contract():
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
