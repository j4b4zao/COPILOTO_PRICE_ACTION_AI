"""Testes da camada diagnóstica inspirada em Brooks Trends, capítulo 25."""

from analysis.price_action.trend_resumption_day_dynamics import (
    TrendResumptionDayDynamics,
)
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def analyze(closed, trend):
    current = candle(0, 9999, -9999, 0)
    return TrendResumptionDayDynamics.analyze([*closed, current], trend)


def teste_retomada_alta_apos_pausa():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 106, 101, 105),
        candle(105, 109, 104, 108),
        candle(108, 109, 106, 107),
        candle(107, 108, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 111, 106, 110),
        candle(110, 114, 109, 113),
        candle(113, 117, 112, 116),
    ]
    result = analyze(closed, Trend.UP)
    assert result["brooks_resumption_direction"] == "BUY"
    assert result["brooks_resumption_breakout"] is True
    assert result["brooks_resumption_confirmed"] is True


def teste_retomada_baixa_apos_pausa():
    closed = [
        candle(116, 117, 112, 113),
        candle(113, 114, 109, 110),
        candle(110, 111, 106, 107),
        candle(107, 109, 106, 108),
        candle(108, 110, 107, 109),
        candle(109, 110, 107, 108),
        candle(108, 109, 104, 105),
        candle(105, 106, 101, 102),
        candle(102, 103, 98, 99),
    ]
    result = analyze(closed, Trend.DOWN)
    assert result["brooks_resumption_direction"] == "SELL"
    assert result["brooks_resumption_breakout"] is True
    assert result["brooks_resumption_confirmed"] is True


def teste_pausa_sem_rompimento_nao_confirma():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 106, 101, 105),
        candle(105, 109, 104, 108),
        candle(108, 109, 106, 107),
        candle(107, 108, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 109, 106, 108),
        candle(108, 109, 107, 108.5),
        candle(108.5, 109, 107.5, 108),
    ]
    result = analyze(closed, Trend.UP)
    assert result["brooks_resumption_confirmed"] is False


def teste_reversao_forte_nao_deve_ser_chamada_retomada():
    closed = [
        candle(100, 104, 99, 103),
        candle(103, 107, 102, 106),
        candle(106, 110, 105, 109),
        candle(109, 110, 105, 106),
        candle(106, 107, 101, 102),
        candle(102, 103, 97, 98),
        candle(98, 99, 94, 95),
        candle(95, 96, 91, 92),
        candle(92, 93, 88, 89),
    ]
    result = analyze(closed, Trend.UP)
    assert result["brooks_resumption_confirmed"] is False


def teste_candle_atual_nao_pode_criar_retomada():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 106, 101, 105),
        candle(105, 109, 104, 108),
        candle(108, 109, 106, 107),
        candle(107, 108, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 109, 106, 108),
        candle(108, 109, 107, 108.5),
        candle(108.5, 109, 107.5, 108),
    ]
    current = candle(108, 120, 107, 119)
    result = TrendResumptionDayDynamics.analyze([*closed, current], Trend.UP)
    assert result["brooks_resumption_confirmed"] is False


def teste_historico_insuficiente():
    result = analyze(
        [
            candle(100, 102, 99, 101),
            candle(101, 103, 100, 102),
            candle(102, 104, 101, 103),
        ],
        Trend.UP,
    )
    assert result["brooks_resumption_valid"] is False
