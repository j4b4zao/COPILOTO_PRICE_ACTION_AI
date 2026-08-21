"""Testes do Capítulo 6 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


WARMUP = (
    candle(100.0, 104.0, 98.0, 102.0),
    candle(102.0, 106.0, 100.0, 104.0),
    candle(104.0, 108.0, 102.0, 106.0),
    candle(106.0, 110.0, 104.0, 108.0),
    candle(108.0, 112.0, 106.0, 110.0),
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


def teste_reversao_de_duas_barras():
    result = analyze((
        candle(110.0, 111.0, 101.0, 102.0),
        candle(102.0, 112.0, 101.0, 111.0),
    ))
    assert result.brooks_two_bar_reversal is True
    assert result.brooks_two_bar_direction == "BULL"
    assert result.brooks_composite_pattern == "TWO_BAR_REVERSAL"


def teste_reversao_de_tres_barras_com_pausa():
    result = analyze((
        candle(110.0, 111.0, 101.0, 102.0),
        candle(102.0, 104.0, 100.0, 102.0),
        candle(102.0, 112.0, 101.0, 111.0),
    ))
    assert result.brooks_three_bar_reversal is True
    assert result.brooks_three_bar_direction == "BULL"
    assert result.brooks_composite_pattern == "THREE_BAR_REVERSAL"


def teste_sequencia_ii_e_identificada():
    result = analyze((
        candle(100.0, 115.0, 90.0, 108.0),
        candle(108.0, 112.0, 94.0, 106.0),
        candle(106.0, 110.0, 96.0, 107.0),
    ), trend=Trend.UNKNOWN)
    assert result.brooks_inside_sequence_count == 2
    assert result.brooks_composite_pattern == "II"
    assert result.brooks_composite_direction == "BOTH"


def teste_padrao_ioi_e_identificado():
    result = analyze((
        candle(100.0, 115.0, 90.0, 108.0),
        candle(108.0, 112.0, 94.0, 106.0),
        candle(106.0, 118.0, 88.0, 109.0),
        candle(109.0, 114.0, 92.0, 108.0),
    ), trend=Trend.UNKNOWN)
    assert result.brooks_ioi_pattern is True
    assert result.brooks_composite_pattern == "IOI"


def teste_micro_fundo_duplo():
    result = analyze((
        candle(105.0, 106.0, 99.0, 100.0),
        candle(100.0, 105.0, 99.4, 104.0),
    ), trend=Trend.UNKNOWN)
    assert result.brooks_micro_double_bottom is True
    assert result.brooks_composite_pattern == "TWO_BAR_REVERSAL"


def teste_barra_raspada_e_informativa():
    result = analyze((
        candle(109.0, 113.0, 108.0, 112.0),
        candle(112.0, 118.0, 111.0, 118.0),
    ))
    assert result.brooks_shaved_top is True
    assert result.brooks_shaved_trend_bar is True


def teste_falha_de_barra_de_reversao_rompe_lado_oposto():
    result = analyze((
        candle(106.0, 112.0, 100.0, 111.0),
        candle(111.0, 112.0, 99.0, 110.0),
    ), trend=Trend.UNKNOWN)
    assert result.brooks_failed_reversal is True
    assert result.brooks_failed_reversal_direction == "DOWN"
    assert result.brooks_composite_pattern == "FAILED_REVERSAL"


def teste_barra_de_exaustao_apos_corrida_longa():
    run = tuple(
        candle(100.0 + index, 102.0 + index, 99.5 + index, 101.0 + index)
        for index in range(11)
    )
    exhaustion = candle(111.0, 120.0, 110.5, 119.0)
    result = analyze((*run, exhaustion), trend=Trend.UP)
    assert result.brooks_exhaustion_bar is True
    assert result.brooks_composite_pattern == "EXHAUSTION_BAR"


def teste_candle_atual_nao_contamina_e_normal_renko_sao_iguais():
    closed = (
        candle(110.0, 111.0, 101.0, 102.0),
        candle(102.0, 112.0, 101.0, 111.0),
    )
    normal = analyze(closed, timeframe="M1")
    renko = analyze(
        closed,
        timeframe="RENKO_20",
        current=candle(111.0, 300.0, 10.0, 20.0),
    )
    assert normal.brooks_composite_pattern == renko.brooks_composite_pattern
    assert normal.brooks_composite_direction == renko.brooks_composite_direction


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    baseline = analyze((candle(110.0, 114.0, 108.0, 112.0),))
    reversal = analyze((
        candle(110.0, 111.0, 101.0, 102.0),
        candle(102.0, 112.0, 101.0, 111.0),
    ))
    assert baseline.score == reversal.score
    assert baseline.bias == reversal.bias == "BUY"
    assert baseline.bos is reversal.bos is False
    assert baseline.choch is reversal.choch is False


def teste_clear_remove_estado_composto():
    result = analyze((
        candle(110.0, 111.0, 101.0, 102.0),
        candle(102.0, 112.0, 101.0, 111.0),
    ))
    result.clear()
    assert result.brooks_composite_pattern == "NONE"
    assert result.brooks_two_bar_reversal is False
    assert result.brooks_inside_sequence_count == 0
    assert result.brooks_exhaustion_bar is False


if __name__ == "__main__":
    tests = (
        teste_reversao_de_duas_barras,
        teste_reversao_de_tres_barras_com_pausa,
        teste_sequencia_ii_e_identificada,
        teste_padrao_ioi_e_identificado,
        teste_micro_fundo_duplo,
        teste_barra_raspada_e_informativa,
        teste_falha_de_barra_de_reversao_rompe_lado_oposto,
        teste_barra_de_exaustao_apos_corrida_longa,
        teste_candle_atual_nao_contamina_e_normal_renko_sao_iguais,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_estado_composto,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 6 composite signal patterns")
