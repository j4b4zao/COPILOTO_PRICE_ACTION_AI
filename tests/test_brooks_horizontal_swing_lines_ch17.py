"""Testes do capítulo 17 de Trading Price Action Trends."""

from analysis.price_action.horizontal_swing_dynamics import (
    HorizontalSwingDynamics,
)
from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def resistance_base():
    return [
        candle(100, 103, 99, 102),
        candle(102, 110, 101, 105),
        candle(105, 107, 103, 104),
        candle(104, 108, 102, 106),
    ]


def support_base():
    return [
        candle(110, 111, 107, 108),
        candle(108, 109, 100, 104),
        candle(104, 107, 103, 106),
        candle(106, 108, 102, 104),
    ]


def analyze(closed, trend=Trend.SIDEWAYS):
    return HorizontalSwingDynamics.analyze(
        [*closed, candle(0, 1000, -1000, 0)],
        trend,
    )


def integrated(timeframe="M1", current=None):
    closed = [
        *resistance_base(),
        candle(106, 109.6, 104, 107),
    ]
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for item in closed:
        market.candles.add(item)
    market.candles.add(current or candle(0, 1, -1, 0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = Trend.SIDEWAYS
    PriceAction().executar(context)
    return context.price_action


def teste_maxima_de_swing_cria_resistencia_horizontal():
    metrics = analyze([*resistance_base(), candle(106, 109.6, 104, 107)])
    assert metrics["brooks_horizontal_level_type"] == "RESISTANCE"
    assert metrics["brooks_horizontal_level"] == 110
    assert metrics["brooks_horizontal_state"] == "LEVEL_TEST"
    assert metrics["brooks_horizontal_tested"] is True


def teste_minima_de_swing_cria_suporte_horizontal():
    metrics = analyze([*support_base(), candle(104, 106, 100.4, 105)])
    assert metrics["brooks_horizontal_level_type"] == "SUPPORT"
    assert metrics["brooks_horizontal_level"] == 100
    assert metrics["brooks_horizontal_state"] == "LEVEL_TEST"


def teste_fechamento_acima_da_resistencia_confirma_rompimento():
    metrics = analyze([*resistance_base(), candle(106, 112, 105, 111)])
    assert metrics["brooks_horizontal_state"] == "BREAKOUT"
    assert metrics["brooks_horizontal_broken"] is True
    assert metrics["brooks_horizontal_break_direction"] == "UP"


def teste_fechamento_abaixo_do_suporte_confirma_rompimento():
    metrics = analyze([*support_base(), candle(104, 105, 97, 98)])
    assert metrics["brooks_horizontal_state"] == "BREAKOUT"
    assert metrics["brooks_horizontal_break_direction"] == "DOWN"


def teste_retorno_abaixo_da_resistencia_e_fuga_falhada():
    closed = [*resistance_base(), candle(106, 112, 105, 111), candle(111, 112, 108, 109)]
    metrics = analyze(closed)
    assert metrics["brooks_horizontal_state"] == "FAILED_BREAKOUT"
    assert metrics["brooks_horizontal_returned_inside"] is True


def teste_retorno_acima_do_suporte_e_fuga_falhada():
    closed = [*support_base(), candle(104, 105, 97, 98), candle(98, 102, 97, 101)]
    metrics = analyze(closed)
    assert metrics["brooks_horizontal_state"] == "FAILED_BREAKOUT"
    assert metrics["brooks_horizontal_returned_inside"] is True


def teste_reteste_do_rompimento_e_pullback_de_fuga():
    closed = [*resistance_base(), candle(106, 112, 105, 111), candle(111, 113, 110.2, 112)]
    metrics = analyze(closed, Trend.UP)
    assert metrics["brooks_horizontal_state"] == "BREAKOUT_PULLBACK"
    assert metrics["brooks_horizontal_breakout_pullback"] is True
    assert metrics["brooks_horizontal_context"] == "TREND_PULLBACK"


def teste_segundo_teste_do_nivel_e_identificado():
    closed = [
        *resistance_base(),
        candle(106, 109.6, 104, 107),
        candle(107, 108, 104, 106),
        candle(106, 109.7, 105, 108),
    ]
    metrics = analyze(closed)
    assert metrics["brooks_horizontal_test_count"] >= 2
    assert metrics["brooks_horizontal_second_attempt"] is True


def teste_fade_contra_tendencia_forte_recebe_alerta_de_risco():
    metrics = analyze(
        [*resistance_base(), candle(106, 109.6, 104, 107)],
        Trend.UP,
    )
    assert metrics["brooks_horizontal_countertrend_risk"] is True
    assert metrics["brooks_horizontal_context"] == "TREND_REFERENCE"


def teste_candle_atual_nao_contamina_o_nivel():
    normal = integrated()
    extreme = integrated(current=candle(500, 1000, -1000, -500))
    assert normal.brooks_horizontal_state == extreme.brooks_horizontal_state
    assert normal.brooks_horizontal_level == extreme.brooks_horizontal_level


def teste_mesma_leitura_em_normal_e_renko():
    normal = integrated(timeframe="M1")
    renko = integrated(timeframe="RENKO_20")
    assert normal.brooks_horizontal_state == renko.brooks_horizontal_state
    assert normal.brooks_horizontal_level == renko.brooks_horizontal_level


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    result = integrated()
    before = (result.score, result.bias, result.bos, result.choch)
    HorizontalSwingDynamics.analyze([], result.trend)
    after = (result.score, result.bias, result.bos, result.choch)
    assert after == before


def teste_clear_remove_o_nivel_anterior():
    result = integrated()
    result.clear()
    assert result.brooks_horizontal_state == "NO_LEVEL"
    assert result.brooks_horizontal_level_type == "NONE"
    assert result.brooks_horizontal_valid is False
    assert result.brooks_horizontal_second_attempt is False


if __name__ == "__main__":
    tests = (
        teste_maxima_de_swing_cria_resistencia_horizontal,
        teste_minima_de_swing_cria_suporte_horizontal,
        teste_fechamento_acima_da_resistencia_confirma_rompimento,
        teste_fechamento_abaixo_do_suporte_confirma_rompimento,
        teste_retorno_abaixo_da_resistencia_e_fuga_falhada,
        teste_retorno_acima_do_suporte_e_fuga_falhada,
        teste_reteste_do_rompimento_e_pullback_de_fuga,
        teste_segundo_teste_do_nivel_e_identificado,
        teste_fade_contra_tendencia_forte_recebe_alerta_de_risco,
        teste_candle_atual_nao_contamina_o_nivel,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_o_nivel_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 17 horizontal swing lines")
