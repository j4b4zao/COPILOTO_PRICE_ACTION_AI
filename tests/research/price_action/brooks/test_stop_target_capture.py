from tools.profit_rtd_brooks_stop_target_capture import enrich_price_action_snapshot


def _item(direction="BUY", *, triggered=True, close=100, low=95, high=103, range_valid=True):
    return {
        "price_action": {
            "brooks_signal_direction": direction,
            "brooks_entry_triggered": triggered,
            "brooks_trading_range_valid": range_valid,
            "brooks_trading_range_low": 90,
            "brooks_trading_range_high": 110,
        },
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "ohlc_ready": True,
            "candle_id": "WINV26|M1|1",
            "close": close,
            "low": low,
            "high": high,
        },
    }


def test_buy_captures_signal_bar_stop_and_range_target():
    pa = enrich_price_action_snapshot(_item())["price_action"]
    assert pa["brooks_stop_target_capture_status"] == "ELIGIBLE"
    assert pa["brooks_stop_target_initial_stop"] == 95
    assert pa["brooks_stop_target_target_price"] == 110
    assert pa["brooks_stop_target_reward_risk"] == 2


def test_sell_captures_mirrored_geometry():
    pa = enrich_price_action_snapshot(
        _item("SELL", close=100, low=97, high=105)
    )["price_action"]
    assert pa["brooks_stop_target_initial_stop"] == 105
    assert pa["brooks_stop_target_target_price"] == 90
    assert pa["brooks_stop_target_reward_risk"] == 2


def test_not_triggered_never_becomes_eligible():
    pa = enrich_price_action_snapshot(_item(triggered=False))["price_action"]
    assert pa["brooks_stop_target_capture_status"] == "NOT_ELIGIBLE"
    assert "ENTRY_NOT_TRIGGERED" in pa["brooks_stop_target_reasons"]


def test_no_range_records_stop_but_does_not_invent_target():
    pa = enrich_price_action_snapshot(_item(range_valid=False))["price_action"]
    assert pa["brooks_stop_target_stop_geometry_valid"] is True
    assert pa["brooks_stop_target_target_valid"] is False
    assert pa["brooks_stop_target_target_price"] == 0
    assert pa["brooks_stop_target_target_source"] == "NONE"


def test_flat_signal_candle_rejects_zero_risk_geometry():
    pa = enrich_price_action_snapshot(_item(close=100, low=100))["price_action"]
    assert pa["brooks_stop_target_capture_status"] == "NOT_ELIGIBLE"
    assert pa["brooks_stop_target_reward_risk"] == 0


def test_capture_is_strictly_non_operational():
    pa = enrich_price_action_snapshot(_item())["price_action"]
    assert pa["brooks_stop_target_research_only"] is True
    assert pa["brooks_stop_target_observational_only"] is True
    assert pa["brooks_stop_target_predictive_claim_allowed"] is False
    assert pa["brooks_stop_target_score_influence_allowed"] is False
    assert pa["brooks_stop_target_risk_influence_allowed"] is False
    assert pa["brooks_stop_target_decision_influence_allowed"] is False
    assert pa["brooks_stop_target_alert_influence_allowed"] is False
    assert pa["brooks_stop_target_order_execution_allowed"] is False
