"""Testes do Capítulo 2 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
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


def analyze(closed, current=None):
    market = MarketState(
        symbol="WINV26",
        timeframe="M1",
    )

    for item in closed:
        market.candles.add(item)

    market.candles.add(
        current or candle(0.0, 1.0, -1.0, 0.0)
    )

    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = Trend.UP
    PriceAction().executar(context)
    return context.price_action


REFERENCE = (
    candle(100.0, 104.0, 99.0, 103.0),
    candle(103.0, 107.0, 102.0, 106.0),
    candle(106.0, 110.0, 105.0, 109.0),
    candle(109.0, 113.0, 108.0, 112.0),
    candle(112.0, 116.0, 111.0, 115.0),
)


def teste_barra_tendencia_forte_e_climax_ativo():
    result = analyze(
        (*REFERENCE, candle(115.0, 122.0, 114.5, 121.5))
    )

    assert result.bar_classification == "TREND_BAR"
    assert result.bar_direction == "BULL"
    assert result.body_ratio > 0.80
    assert result.relative_body_ratio > 2.0
    assert result.close_position > 0.90
    assert result.trend_bar_strength == "STRONG"
    assert result.climax_active is True
    assert result.climax_direction == "BULL"
    assert result.climax_length == 6
    assert result.climax_ended is False


def teste_doji_encerra_climax_de_compra():
    result = analyze(
        (
            *REFERENCE,
            candle(115.0, 117.0, 113.0, 115.1),
        )
    )

    assert result.bar_classification == "DOJI"
    assert result.trend_bar_strength == "DOJI"
    assert result.pause_detected is True
    assert result.climax_active is False
    assert result.climax_ended is True
    assert result.climax_direction == "BULL"
    assert result.climax_length == 5


def teste_inside_bar_com_cauda_encerra_climax():
    result = analyze(
        (
            *REFERENCE,
            candle(114.0, 115.5, 112.0, 115.0),
        )
    )

    assert result.bar_classification == "TREND_BAR"
    assert result.pause_detected is True
    assert result.climax_ended is True
    assert result.climax_direction == "BULL"


def teste_barra_oposta_encerra_climax():
    result = analyze(
        (
            *REFERENCE,
            candle(115.0, 116.0, 109.0, 110.0),
        )
    )

    assert result.bar_direction == "BEAR"
    assert result.pause_detected is True
    assert result.climax_ended is True
    assert result.climax_direction == "BULL"
    assert result.climax_length == 5


def teste_candle_em_formacao_nao_contamina_dinamica():
    closed = (
        *REFERENCE,
        candle(115.0, 122.0, 114.5, 121.5),
    )
    first = analyze(closed)
    second = analyze(
        closed,
        current=candle(121.5, 300.0, 10.0, 20.0),
    )

    assert first.body_ratio == second.body_ratio
    assert (
        first.relative_body_ratio
        == second.relative_body_ratio
    )
    assert first.climax_length == second.climax_length
    assert first.climax_active == second.climax_active


def teste_dinamica_nao_adiciona_score():
    baseline = analyze(REFERENCE)
    strong = analyze(
        (*REFERENCE, candle(115.0, 122.0, 114.5, 121.5))
    )

    assert baseline.score == strong.score
    assert baseline.bias == strong.bias == "BUY"


def teste_clear_remove_dinamica_anterior():
    result = analyze(
        (*REFERENCE, candle(115.0, 122.0, 114.5, 121.5))
    )
    result.clear()

    assert result.bar_classification == "UNKNOWN"
    assert result.bar_direction == "NONE"
    assert result.body_ratio == 0.0
    assert result.relative_body_ratio == 0.0
    assert result.close_position == 0.5
    assert result.trend_bar_strength == "UNKNOWN"
    assert result.climax_direction == "NONE"
    assert result.climax_length == 0
    assert result.climax_active is False
    assert result.climax_ended is False
    assert result.pause_detected is False


if __name__ == "__main__":
    tests = (
        teste_barra_tendencia_forte_e_climax_ativo,
        teste_doji_encerra_climax_de_compra,
        teste_inside_bar_com_cauda_encerra_climax,
        teste_barra_oposta_encerra_climax,
        teste_candle_em_formacao_nao_contamina_dinamica,
        teste_dinamica_nao_adiciona_score,
        teste_clear_remove_dinamica_anterior,
    )

    for test in tests:
        test()

    print("OK - Brooks Trends chapter 2 bar dynamics")
