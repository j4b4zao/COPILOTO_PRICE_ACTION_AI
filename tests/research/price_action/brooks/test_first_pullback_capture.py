from types import SimpleNamespace

from tools.profit_rtd_brooks_first_pullback_capture import (
    enrich_price_action_snapshot,
    snapshot_first_pullback,
)


class Candle:
    def __init__(self, open_, high, low, close):
        self.open = float(open_)
        self.high = float(high)
        self.low = float(low)
        self.close = float(close)


def _context(candles):
    return SimpleNamespace(
        market=SimpleNamespace(
            candles=SimpleNamespace(all=lambda: list(candles)),
        )
    )


def _uptrend_with_pullback():
    candles = []
    price = 100.0
    for _ in range(14):
        candles.append(Candle(price, price + 2.0, price - 0.5, price + 1.5))
        price += 1.5
    candles.extend([
        Candle(price, price + 0.5, price - 1.5, price - 1.0),
        Candle(price - 1.0, price - 0.5, price - 2.0, price - 1.5),
        Candle(price - 1.5, price + 1.0, price - 2.0, price + 0.5),
    ])
    return candles


def test_snapshot_exposes_required_auditor_fields():
    result = snapshot_first_pullback(_context(_uptrend_with_pullback()))
    required = {
        "brooks_first_pullback_valid",
        "brooks_first_pullback_direction",
        "brooks_first_pullback_stage",
        "brooks_first_pullback_stage_index",
        "brooks_first_pullback_continuation_bias",
        "brooks_first_pullback_reversal_risk",
        "brooks_first_pullback_trading_range_transition",
    }
    assert required.issubset(result)


def test_snapshot_uses_diagnostic_contract_without_operational_influence():
    result = snapshot_first_pullback(_context(_uptrend_with_pullback()))
    assert result["research_only"] is True
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False


def test_enrich_places_fields_inside_price_action_block():
    item = {"price_action": {"brooks_signal_phase": "SETUP_PENDING"}}
    out = enrich_price_action_snapshot(item, _context(_uptrend_with_pullback()))
    assert out is item
    assert "brooks_first_pullback_stage" in out["price_action"]
    assert out["price_action"]["brooks_signal_phase"] == "SETUP_PENDING"


def test_insufficient_history_is_explicit_not_fabricated():
    result = snapshot_first_pullback(_context([Candle(100, 101, 99, 100.5)] * 5))
    assert result["brooks_first_pullback_valid"] is False
    assert result["brooks_first_pullback_stage"] == "NO_SEQUENCE"
    assert "INSUFFICIENT_HISTORY" in result["brooks_first_pullback_reasons"]
