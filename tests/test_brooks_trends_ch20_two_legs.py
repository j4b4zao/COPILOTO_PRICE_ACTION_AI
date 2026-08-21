"""Testes do capítulo 20 de Trading Price Action Trends."""

from analysis.price_action.two_leg_dynamics import TwoLegDynamics
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


def analyze(closed, trend):
    current = candle(0, 1000, -1000, 0)
    return TwoLegDynamics.analyze([*closed, current], trend)


def teste_tendencia_de_alta_detecta_pullback_de_duas_pernas():
    closed = [
        candle(100, 102, 99, 101),
        candle(101, 105, 100, 104),
        candle(104, 110, 103, 109),
        candle(109, 109, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 107, 102, 103),
        candle(103, 106, 102, 105),
    ]

    metrics = analyze(closed, Trend.UP)

    assert metrics["brooks_two_leg_state"] == "TWO_LEG_COMPLETE"
    assert metrics["brooks_two_leg_direction"] == "BUY"
    assert metrics["brooks_two_leg_setup"] == "HIGH_2"
    assert metrics["brooks_two_leg_leg_count"] == 2
    assert metrics["brooks_two_leg_second_leg_present"] is True
    assert metrics["brooks_two_leg_second_leg_completed"] is True
    assert metrics["brooks_two_leg_entry_candidate"] is True
    assert metrics["brooks_two_leg_quality"] == "HIGH"


def teste_tendencia_de_baixa_detecta_pullback_de_duas_pernas():
    closed = [
        candle(110, 111, 108, 109),
        candle(109, 110, 104, 105),
        candle(105, 106, 100, 101),
        candle(101, 105, 101, 104),
        candle(104, 105, 102, 103),
        candle(103, 108, 103, 107),
        candle(107, 107, 104, 105),
    ]

    metrics = analyze(closed, Trend.DOWN)

    assert metrics["brooks_two_leg_state"] == "TWO_LEG_COMPLETE"
    assert metrics["brooks_two_leg_direction"] == "SELL"
    assert metrics["brooks_two_leg_setup"] == "LOW_2"
    assert metrics["brooks_two_leg_leg_count"] == 2
    assert metrics["brooks_two_leg_entry_candidate"] is True


def teste_primeira_perna_ainda_nao_cria_high_2():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 107, 101, 106),
        candle(106, 110, 105, 109),
        candle(109, 109, 105, 106),
        candle(106, 108, 105, 107),
    ]

    metrics = analyze(closed, Trend.UP)

    assert metrics["brooks_two_leg_state"] == "LEG_1"
    assert metrics["brooks_two_leg_setup"] == "NONE"
    assert metrics["brooks_two_leg_entry_candidate"] is False


def teste_segunda_perna_em_andamento_nao_antecipa_entrada():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 107, 101, 106),
        candle(106, 110, 105, 109),
        candle(109, 109, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 107, 102, 103),
    ]

    metrics = analyze(closed, Trend.UP)

    assert metrics["brooks_two_leg_state"] == "LEG_2"
    assert metrics["brooks_two_leg_second_leg_present"] is True
    assert metrics["brooks_two_leg_second_leg_completed"] is False
    assert metrics["brooks_two_leg_entry_candidate"] is False


def teste_segunda_perna_pode_estender_a_primeira():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 107, 101, 106),
        candle(106, 110, 105, 109),
        candle(109, 109, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 107, 101, 102),
        candle(102, 105, 101, 104),
    ]

    metrics = analyze(closed, Trend.UP)

    assert metrics["brooks_two_leg_second_extends_first"] is True
    assert metrics["brooks_two_leg_setup"] == "HIGH_2"


def teste_terceira_perna_classifica_pullback_estendido():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 107, 101, 106),
        candle(106, 110, 105, 109),
        candle(109, 109, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 107, 102, 103),
        candle(103, 106, 102, 105),
        candle(105, 105, 100, 101),
    ]

    metrics = analyze(closed, Trend.UP)

    assert metrics["brooks_two_leg_state"] == "EXTENDED_PULLBACK"
    assert metrics["brooks_two_leg_leg_count"] == 3
    assert metrics["brooks_two_leg_extended"] is True
    assert metrics["brooks_two_leg_quality"] == "LOW"


def teste_lateral_nao_gera_duas_pernas_de_tendencia():
    closed = [
        candle(100, 102, 99, 101),
        candle(101, 103, 100, 102),
        candle(102, 104, 101, 103),
        candle(103, 104, 101, 102),
        candle(102, 103, 100, 101),
    ]

    metrics = analyze(closed, Trend.SIDEWAYS)

    assert metrics["brooks_two_leg_state"] == "NO_TREND"
    assert metrics["brooks_two_leg_valid"] is False
    assert metrics["brooks_two_leg_entry_candidate"] is False


def teste_candle_atual_e_excluido_da_confirmacao():
    closed = [
        candle(100, 103, 99, 102),
        candle(102, 107, 101, 106),
        candle(106, 110, 105, 109),
        candle(109, 109, 105, 106),
        candle(106, 108, 105, 107),
        candle(107, 107, 102, 103),
    ]

    current = candle(103, 120, 102, 119)
    metrics = TwoLegDynamics.analyze([*closed, current], Trend.UP)

    assert metrics["brooks_two_leg_state"] == "LEG_2"
    assert metrics["brooks_two_leg_second_leg_completed"] is False
    assert metrics["brooks_two_leg_entry_candidate"] is False
