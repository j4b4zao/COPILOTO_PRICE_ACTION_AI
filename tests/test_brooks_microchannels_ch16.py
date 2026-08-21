"""Testes do capítulo 16 de Trading Price Action Trends."""

from analysis.price_action.microchannel_dynamics import MicrochannelDynamics
from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def bull_closed():
    return [
        candle(100, 104, 99, 103),
        candle(102, 106, 101, 105),
        candle(104, 108, 103, 107),
        candle(106, 110, 105, 109),
        candle(108, 112, 107, 111),
    ]


def bear_closed():
    return [
        candle(112, 113, 108, 109),
        candle(110, 111, 106, 107),
        candle(108, 109, 104, 105),
        candle(106, 107, 102, 103),
        candle(104, 105, 100, 101),
    ]


def analyze(closed, trend):
    return MicrochannelDynamics.analyze(
        [*closed, candle(0, 1000, -1000, 0)],
        trend,
    )


def integrated(timeframe="M1", current=None):
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for item in bull_closed():
        market.candles.add(item)
    market.candles.add(current or candle(0, 1, -1, 0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = Trend.UP
    PriceAction().executar(context)
    return context.price_action


def teste_microcanal_de_alta_forte_e_ativo():
    metrics = analyze(bull_closed(), Trend.UP)
    assert metrics["brooks_microchannel_state"] == "ACTIVE"
    assert metrics["brooks_microchannel_direction"] == "UP"
    assert metrics["brooks_microchannel_strength"] == "STRONG"
    assert metrics["brooks_microchannel_bar_count"] == 5


def teste_microcanal_de_baixa_e_simetrico():
    metrics = analyze(bear_closed(), Trend.DOWN)
    assert metrics["brooks_microchannel_direction"] == "DOWN"
    assert metrics["brooks_microchannel_strength"] == "STRONG"
    assert metrics["brooks_microchannel_active"] is True


def teste_tres_barras_formam_microcanal_moderado():
    metrics = analyze(bull_closed()[:3], Trend.UP)
    assert metrics["brooks_microchannel_valid"] is True
    assert metrics["brooks_microchannel_strength"] == "MODERATE"


def teste_duas_barras_nao_confirmam_microcanal():
    metrics = analyze(bull_closed()[:2], Trend.UP)
    assert metrics["brooks_microchannel_state"] == "NO_MICROCHANNEL"
    assert metrics["brooks_microchannel_valid"] is False


def teste_primeira_quebra_de_microcanal_de_alta():
    closed = [*bull_closed(), candle(110, 112, 105, 107)]
    metrics = analyze(closed, Trend.UP)
    assert metrics["brooks_microchannel_state"] == "FIRST_BREAK"
    assert metrics["brooks_microchannel_break_direction"] == "DOWN"
    assert metrics["brooks_microchannel_first_break_failure_risk"] is True
    assert metrics["brooks_microchannel_pullback_count"] == 1


def teste_primeira_quebra_de_microcanal_de_baixa():
    closed = [*bear_closed(), candle(102, 108, 101, 106)]
    metrics = analyze(closed, Trend.DOWN)
    assert metrics["brooks_microchannel_state"] == "FIRST_BREAK"
    assert metrics["brooks_microchannel_break_direction"] == "UP"
    assert metrics["brooks_microchannel_first_break_failure_risk"] is True


def teste_primeira_quebra_preserva_nivel_de_reteste_do_extremo():
    bull = analyze([*bull_closed(), candle(110, 112, 105, 107)], Trend.UP)
    bear = analyze([*bear_closed(), candle(102, 108, 101, 106)], Trend.DOWN)
    assert bull["brooks_microchannel_retest_level"] == 112
    assert bear["brooks_microchannel_retest_level"] == 100


def teste_sem_tendencia_clara_permanece_neutro():
    metrics = analyze(bull_closed(), Trend.SIDEWAYS)
    assert metrics["brooks_microchannel_state"] == "NO_CLEAR_TREND"
    assert metrics["brooks_microchannel_direction"] == "NONE"
    assert metrics["brooks_microchannel_valid"] is False


def teste_candle_atual_nao_contamina_o_diagnostico():
    normal = integrated()
    extreme = integrated(current=candle(500, 1000, -1000, -500))
    assert normal.brooks_microchannel_state == extreme.brooks_microchannel_state
    assert normal.brooks_microchannel_bar_count == extreme.brooks_microchannel_bar_count


def teste_mesma_leitura_em_normal_e_renko():
    normal = integrated(timeframe="M1")
    renko = integrated(timeframe="RENKO_20")
    assert normal.brooks_microchannel_state == renko.brooks_microchannel_state
    assert normal.brooks_microchannel_strength == renko.brooks_microchannel_strength


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    result = integrated()
    before = (result.score, result.bias, result.bos, result.choch)
    MicrochannelDynamics.analyze([], result.trend)
    after = (result.score, result.bias, result.bos, result.choch)
    assert after == before


def teste_clear_remove_o_microcanal_anterior():
    result = integrated()
    result.clear()
    assert result.brooks_microchannel_state == "NO_MICROCHANNEL"
    assert result.brooks_microchannel_direction == "NONE"
    assert result.brooks_microchannel_valid is False
    assert result.brooks_microchannel_first_break_failure_risk is False


if __name__ == "__main__":
    tests = (
        teste_microcanal_de_alta_forte_e_ativo,
        teste_microcanal_de_baixa_e_simetrico,
        teste_tres_barras_formam_microcanal_moderado,
        teste_duas_barras_nao_confirmam_microcanal,
        teste_primeira_quebra_de_microcanal_de_alta,
        teste_primeira_quebra_de_microcanal_de_baixa,
        teste_primeira_quebra_preserva_nivel_de_reteste_do_extremo,
        teste_sem_tendencia_clara_permanece_neutro,
        teste_candle_atual_nao_contamina_o_diagnostico,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_o_microcanal_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 16 microchannels")
