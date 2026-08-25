"""Testes do Capítulo 7 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


WARMUP = (
    candle(100.0, 106.0, 98.0, 104.0),
    candle(104.0, 110.0, 102.0, 108.0),
    candle(108.0, 114.0, 106.0, 112.0),
    candle(112.0, 118.0, 110.0, 116.0),
)


def analyze(closed, *, trend=Trend.UP, timeframe="M1", current=None):
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for item in (*WARMUP, *closed):
        market.candles.add(item)
    market.candles.add(current or candle(0.0, 1.0, -1.0, 0.0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = trend
    PriceAction().executar(context)
    return context.price_action


def teste_barra_externa_direcional_de_alta():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(117.0, 125.0, 112.0, 124.0),
    ))
    assert result.brooks_outside_detected is True
    assert result.brooks_outside_direction == "UP"
    assert result.brooks_outside_classification == "REVERSAL_TRAP"
    assert result.brooks_outside_trapped_side == "BEARS"
    assert result.brooks_outside_context == "WITH_TREND"


def teste_barra_externa_direcional_de_baixa():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(119.0, 122.0, 108.0, 110.0),
    ), trend=Trend.DOWN)
    assert result.brooks_outside_direction == "DOWN"
    assert result.brooks_outside_trapped_side == "BULLS"
    assert result.brooks_outside_context == "WITH_TREND"


def teste_fechamento_central_classifica_faixa_de_uma_barra():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(118.0, 125.0, 110.0, 117.5),
    ))
    assert result.brooks_outside_balanced is True
    assert result.brooks_outside_range_like is True
    assert result.brooks_outside_quality == "BALANCED"
    assert result.brooks_outside_classification == "RANGE_BAR"


def teste_duas_barras_externas_formam_oo_e_ampliam_faixa():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(118.0, 124.0, 110.0, 121.0),
        candle(121.0, 128.0, 106.0, 119.0),
    ))
    assert result.brooks_double_outside is True
    assert result.brooks_outside_range_like is True
    assert result.brooks_outside_classification == "RANGE_BAR"


def teste_follow_through_da_barra_externa_anterior():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(117.0, 125.0, 112.0, 124.0),
        candle(124.0, 129.0, 123.0, 128.0),
    ))
    assert result.brooks_outside_detected is False
    assert result.brooks_outside_follow_through is True
    assert result.brooks_outside_failed is False


def teste_falha_da_barra_externa_anterior():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(117.0, 125.0, 112.0, 124.0),
        candle(124.0, 125.0, 109.0, 111.0),
    ))
    assert result.brooks_outside_failed is True
    assert result.brooks_outside_follow_through is False


def teste_barra_muito_expandida_recebe_alerta_de_risco():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(117.0, 140.0, 95.0, 138.0),
    ))
    assert result.brooks_outside_expansion_ratio >= 1.8
    assert result.brooks_outside_quality == "RISKY_LARGE"


def teste_candle_atual_nao_contamina_e_normal_renko_sao_iguais():
    closed = (
        candle(116.0, 120.0, 114.0, 118.0),
        candle(117.0, 125.0, 112.0, 124.0),
    )
    normal = analyze(closed, timeframe="M1")
    renko = analyze(
        closed,
        timeframe="RENKO_20",
        current=candle(124.0, 300.0, 10.0, 20.0),
    )
    assert normal.brooks_outside_direction == renko.brooks_outside_direction
    assert normal.brooks_outside_quality == renko.brooks_outside_quality


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    baseline = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(118.0, 121.0, 116.0, 120.0),
    ))
    outside = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(117.0, 125.0, 112.0, 124.0),
    ))
    assert baseline.score == outside.score
    assert baseline.bias == outside.bias == "BUY"
    assert baseline.bos is outside.bos is False
    assert baseline.choch is outside.choch is False


def teste_clear_remove_estado_da_barra_externa():
    result = analyze((
        candle(116.0, 120.0, 114.0, 118.0),
        candle(117.0, 125.0, 112.0, 124.0),
    ))
    result.clear()
    assert result.brooks_outside_detected is False
    assert result.brooks_outside_direction == "NONE"
    assert result.brooks_outside_quality == "NONE"
    assert result.brooks_double_outside is False
    assert result.brooks_outside_failed is False


if __name__ == "__main__":
    tests = (
        teste_barra_externa_direcional_de_alta,
        teste_barra_externa_direcional_de_baixa,
        teste_fechamento_central_classifica_faixa_de_uma_barra,
        teste_duas_barras_externas_formam_oo_e_ampliam_faixa,
        teste_follow_through_da_barra_externa_anterior,
        teste_falha_da_barra_externa_anterior,
        teste_barra_muito_expandida_recebe_alerta_de_risco,
        teste_candle_atual_nao_contamina_e_normal_renko_sao_iguais,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_estado_da_barra_externa,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 7 outside bar context")
