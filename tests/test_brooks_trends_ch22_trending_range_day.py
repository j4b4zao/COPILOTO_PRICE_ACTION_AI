"""Testes da camada inspirada no capítulo 22 de Trading Price Action Trends."""

from analysis.price_action.trending_range_day_dynamics import (
    TrendingRangeDayDynamics,
)
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


def analyze(closed, trend=Trend.UNKNOWN):
    current = candle(0, 1000, -1000, 0)
    return TrendingRangeDayDynamics.analyze(
        [*closed, current],
        trend=trend,
    )


def bullish_trending_range_day():
    return [
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 104, 101, 103),
        candle(103, 104, 101, 102),
        candle(102, 103, 100, 101),
        candle(101, 103, 100, 102),
        candle(102, 106, 102, 105),
        candle(105, 107, 104, 106),
        candle(106, 108, 105, 107),
        candle(107, 108, 105, 106),
        candle(106, 109, 105, 108),
        candle(108, 109, 106, 107),
        candle(107, 110, 106, 109),
        candle(109, 111, 108, 110),
    ]


def bearish_trending_range_day():
    return [
        candle(110, 111, 108, 109),
        candle(109, 110, 107, 108),
        candle(108, 109, 106, 107),
        candle(107, 110, 106, 108),
        candle(108, 110, 107, 109),
        candle(109, 110, 107, 108),
        candle(108, 108, 104, 105),
        candle(105, 106, 103, 104),
        candle(104, 105, 102, 103),
        candle(103, 105, 102, 104),
        candle(104, 105, 101, 102),
        candle(102, 104, 101, 103),
        candle(103, 104, 100, 101),
        candle(101, 102, 99, 100),
    ]


def teste_detecta_breakout_de_alta_apos_faixa_inicial():
    metrics = analyze(
        bullish_trending_range_day(),
        Trend.UP,
    )

    assert metrics["brooks_trending_range_valid"] is True
    assert metrics["brooks_trending_range_breakout"] is True
    assert metrics["brooks_trending_range_breakout_direction"] == "UP"
    assert metrics["brooks_trending_range_direction"] == "BUY"


def teste_detecta_segunda_faixa_apos_rompimento():
    metrics = analyze(
        bullish_trending_range_day(),
        Trend.UP,
    )

    assert metrics["brooks_trending_range_second_range"] is True
    assert metrics["brooks_trending_range_state"] in (
        "SECOND_RANGE",
        "REVERSAL_RISK",
    )


def teste_detecta_breakout_de_baixa_simetrico():
    metrics = analyze(
        bearish_trending_range_day(),
        Trend.DOWN,
    )

    assert metrics["brooks_trending_range_valid"] is True
    assert metrics["brooks_trending_range_breakout_direction"] == "DOWN"
    assert metrics["brooks_trending_range_direction"] == "SELL"


def teste_alinhamento_com_estrutura():
    metrics = analyze(
        bullish_trending_range_day(),
        Trend.UP,
    )

    assert metrics["brooks_trending_range_aligned_with_structure"] is True


def teste_desalinhamento_com_estrutura():
    metrics = analyze(
        bullish_trending_range_day(),
        Trend.DOWN,
    )

    assert metrics["brooks_trending_range_aligned_with_structure"] is False


def teste_movimento_medido_e_calculado():
    metrics = analyze(
        bullish_trending_range_day(),
        Trend.UP,
    )

    assert metrics["brooks_trending_range_measured_target"] > 0.0


def teste_sem_breakout_permanece_opening_range():
    closed = [
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 103, 100, 101),
        candle(101, 102, 99, 100),
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 103, 100, 101),
        candle(101, 102, 99, 100),
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 103, 100, 101),
        candle(101, 102, 99, 100),
    ]

    metrics = analyze(closed)

    assert metrics["brooks_trending_range_state"] == "OPENING_RANGE"
    assert metrics["brooks_trending_range_breakout"] is False


def teste_travessia_da_faixa_anterior_aumenta_risco_de_reversao():
    closed = [
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 104, 101, 103),
        candle(103, 104, 101, 102),
        candle(102, 103, 100, 101),
        candle(101, 103, 100, 102),
        candle(102, 106, 102, 105),
        candle(105, 107, 104, 106),
        candle(106, 107, 102, 103),
        candle(103, 104, 99, 100),
        candle(100, 102, 98, 99),
        candle(99, 101, 98, 100),
    ]

    metrics = analyze(closed, Trend.UP)

    assert metrics["brooks_trending_range_prior_range_traversed"] is True
    assert metrics["brooks_trending_range_reversal_risk"] is True
    assert metrics["brooks_trending_range_state"] == "REVERSAL_RISK"


def teste_candle_atual_nao_confirma_breakout():
    closed = [
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 103, 100, 101),
        candle(101, 102, 99, 100),
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 103, 100, 101),
        candle(101, 102, 99, 100),
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 103, 100, 101),
        candle(101, 102, 99, 100),
    ]

    current_breakout = candle(100, 120, 99, 118)
    metrics = TrendingRangeDayDynamics.analyze(
        [*closed, current_breakout],
        Trend.UP,
    )

    assert metrics["brooks_trending_range_breakout"] is False
    assert metrics["brooks_trending_range_state"] == "OPENING_RANGE"
