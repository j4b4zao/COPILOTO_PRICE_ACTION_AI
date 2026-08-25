from types import SimpleNamespace

from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from models.book_diagnostics_result import BookDiagnosticsResult
from models.candle import Candle
from enums.trend import Trend


class CandleStore:

    def __init__(self, candles):
        self._candles = candles

    def all(self):
        return list(self._candles)


class FakePriceAction:
    climax_active = False


class FakeContext:

    def __init__(self, candles, trend=Trend.UP, ready=True):
        self.market = SimpleNamespace(
            ready=ready,
            candles=CandleStore(candles),
        )
        self.structure = SimpleNamespace(trend=trend)
        self.price_action = FakePriceAction()
        self.book_diagnostics = BookDiagnosticsResult()


def candle(open_, high, low, close):
    return Candle(
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000,
    )


def bullish_series():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 105, 101, 104),
        candle(104, 107, 103, 106),
        candle(106, 109, 105, 108),
        candle(108, 111, 107, 110),
        candle(110, 113, 109, 112),
        candle(112, 115, 111, 114),
        candle(114, 117, 113, 116),
    ]

    forming = candle(116, 120, 115, 119)

    return closed + [forming]


def test_result_clear_preserves_passive_contract():
    result = BookDiagnosticsResult()

    result.always_in["direction"] = "BUY"
    result.trend_strength["score"] = 90
    result.directional_bias = "BUY"
    result.alignment = "ALIGNED"
    result.quality_score = 90

    result.clear()

    assert result.passive_only is True
    assert result.always_in == {}
    assert result.trend_strength == {}
    assert result.directional_bias == "NONE"
    assert result.alignment == "NEUTRAL"
    assert result.quality_score == 0.0


def test_engine_is_passive_and_synthesizes_alignment():
    context = FakeContext(
        bullish_series(),
        trend=Trend.UP,
    )

    returned = BookDiagnosticsEngine().executar(context)

    result = returned.book_diagnostics

    assert result.valid
    assert result.passive_only is True
    assert result.source == "BookDiagnostics"
    assert result.always_in
    assert result.trend_strength
    assert result.directional_bias in {"BUY", "NONE"}
    assert result.alignment in {
        "ALIGNED",
        "PARTIAL",
        "NEUTRAL",
    }
    assert "PASSIVE_DIAGNOSTICS_ONLY" in result.reasons


def test_market_not_ready_skips_engine():
    context = FakeContext(
        bullish_series(),
        ready=False,
    )

    BookDiagnosticsEngine().executar(context)

    result = context.book_diagnostics

    assert not result.valid
    assert "MARKET_NOT_READY" in result.reasons


def test_forming_candle_does_not_change_book_diagnostics():
    base = bullish_series()[:-1]

    quiet = candle(116, 117, 115, 116)
    explosive = candle(116, 140, 90, 92)

    first = FakeContext(base + [quiet], Trend.UP)
    second = FakeContext(base + [explosive], Trend.UP)

    BookDiagnosticsEngine().executar(first)
    BookDiagnosticsEngine().executar(second)

    assert first.book_diagnostics.always_in == second.book_diagnostics.always_in
    assert first.book_diagnostics.trend_strength == second.book_diagnostics.trend_strength
    assert first.book_diagnostics.directional_bias == second.book_diagnostics.directional_bias
    assert first.book_diagnostics.alignment == second.book_diagnostics.alignment
    assert first.book_diagnostics.quality_score == second.book_diagnostics.quality_score
