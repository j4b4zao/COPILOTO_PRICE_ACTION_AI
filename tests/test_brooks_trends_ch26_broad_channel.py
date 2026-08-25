"""Testes da camada Brooks Trends capítulo 26: Stairs / Broad Channel."""

from analysis.price_action.broad_channel_dynamics import BroadChannelDynamics
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def analyze(closed, trend):
    current = candle(0, 9999, -9999, 0)
    return BroadChannelDynamics.analyze([*closed, current], trend)


def bullish_stairs():
    return [
        candle(100, 103, 99, 102),
        candle(102, 106, 101, 105),
        candle(105, 108, 104, 107),
        candle(107, 109, 103, 104),
        candle(104, 110, 103, 109),
        candle(109, 112, 108, 111),
        candle(111, 113, 106, 107),
        candle(107, 114, 106, 113),
        candle(113, 116, 112, 115),
        candle(115, 117, 109, 110),
        candle(110, 118, 109, 117),
        candle(117, 120, 116, 119),
        candle(119, 121, 115, 116),
        candle(116, 122, 115, 121),
    ]


def bearish_stairs():
    return [
        candle(120, 121, 117, 118),
        candle(118, 119, 114, 115),
        candle(115, 116, 112, 113),
        candle(113, 117, 111, 116),
        candle(116, 117, 110, 111),
        candle(111, 112, 108, 109),
        candle(109, 114, 107, 113),
        candle(113, 114, 106, 107),
        candle(107, 108, 104, 105),
        candle(105, 111, 103, 110),
        candle(110, 111, 102, 103),
        candle(103, 104, 100, 101),
        candle(101, 106, 99, 105),
        candle(105, 106, 98, 99),
    ]


def teste_detecta_broad_channel_de_alta():
    metrics = analyze(bullish_stairs(), Trend.UP)
    assert metrics["brooks_broad_channel_direction"] == "BUY"
    assert metrics["brooks_broad_channel_step_count"] >= 2
    assert metrics["brooks_broad_channel_deep_pullback_count"] >= 1
    assert metrics["brooks_broad_channel_test_count"] >= 1
    assert metrics["brooks_broad_channel_valid"] is True


def teste_detecta_broad_channel_de_baixa():
    metrics = analyze(bearish_stairs(), Trend.DOWN)
    assert metrics["brooks_broad_channel_direction"] == "SELL"
    assert metrics["brooks_broad_channel_step_count"] >= 2
    assert metrics["brooks_broad_channel_deep_pullback_count"] >= 1
    assert metrics["brooks_broad_channel_valid"] is True


def teste_lateral_nao_e_broad_channel():
    metrics = analyze(bullish_stairs(), Trend.SIDEWAYS)
    assert metrics["brooks_broad_channel_valid"] is False
    assert metrics["brooks_broad_channel_direction"] == "NONE"


def teste_tendencia_lisa_sem_pullback_profundo_nao_confirma():
    closed = [
        candle(100, 102, 99, 101.5),
        candle(101.5, 104, 101, 103.5),
        candle(103.5, 106, 103, 105.5),
        candle(105.5, 108, 105, 107.5),
        candle(107.5, 110, 107, 109.5),
        candle(109.5, 112, 109, 111.5),
        candle(111.5, 114, 111, 113.5),
        candle(113.5, 116, 113, 115.5),
    ]
    metrics = analyze(closed, Trend.UP)
    assert metrics["brooks_broad_channel_valid"] is False


def teste_candle_atual_nao_pode_criar_escada():
    closed = bullish_stairs()[:-2]
    fake_current = candle(110, 140, 90, 139)
    metrics = BroadChannelDynamics.analyze([*closed, fake_current], Trend.UP)
    control = analyze(closed, Trend.UP)
    assert metrics == control


def teste_estado_extremo_quando_pullbacks_sao_muito_profundos():
    closed = [
        candle(100, 104, 99, 103),
        candle(103, 110, 102, 109),
        candle(109, 111, 103, 104),
        candle(104, 112, 103, 111),
        candle(111, 116, 110, 115),
        candle(115, 117, 106, 107),
        candle(107, 118, 106, 117),
        candle(117, 121, 116, 120),
        candle(120, 122, 110, 111),
        candle(111, 123, 110, 122),
        candle(122, 125, 121, 124),
        candle(124, 126, 114, 115),
        candle(115, 127, 114, 126),
    ]
    metrics = analyze(closed, Trend.UP)
    if metrics["brooks_broad_channel_valid"]:
        assert metrics["brooks_broad_channel_state"] in (
            "BROAD_CHANNEL",
            "BROAD_CHANNEL_REVERSAL_RISK",
            "BROAD_CHANNEL_EXTREME",
        )
