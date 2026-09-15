from datetime import datetime, timedelta
from types import SimpleNamespace

from core.market_state import MarketState
from models.candle import Candle
from tools.profit_rtd_brooks_trading_range_capture import (
    enrich_price_action_snapshot as enrich_trading_range,
)
from tools.profit_rtd_brooks_wedge_three_pushes_capture import (
    enrich_price_action_snapshot as enrich_three_pushes,
)


def _context_with_real_market_state():
    market = MarketState()
    start = datetime(2026, 9, 15, 10, 0)
    closes = (100, 102, 99, 101, 98, 100, 97, 99, 96, 98, 97, 99, 98, 100, 99)
    for index, close in enumerate(closes):
        candle = Candle(
            timestamp=start + timedelta(minutes=index),
            open=close - 1,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=100 + index,
        )
        market.update(candle, "WINV26", "M1", new_candle=True)
    return SimpleNamespace(market=market)


def test_trading_range_capture_reads_market_state_candles():
    item = enrich_trading_range({"price_action": {}}, _context_with_real_market_state())
    reasons = item["price_action"]["brooks_trading_range_reasons"]
    assert "INSUFFICIENT_HISTORY" not in reasons


def test_three_pushes_capture_reads_market_state_candles(monkeypatch):
    observed = {}

    def analyze(candles):
        observed["count"] = len(candles)
        return SimpleNamespace(
            detected=False,
            push_direction="NONE",
            push_indices=(),
            push_prices=(),
            narrowing=False,
        )

    monkeypatch.setattr(
        "tools.profit_rtd_brooks_wedge_three_pushes_capture."
        "BrooksThreePushesDetector.analyze",
        analyze,
    )
    enrich_three_pushes({"price_action": {}}, _context_with_real_market_state())
    assert observed["count"] == 15
