"""Testes do capítulo 15 de Trading Price Action Trends."""

from types import SimpleNamespace

from analysis.price_action.channel_behavior_dynamics import (
    ChannelBehaviorDynamics,
)
from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def source(**changes):
    values = {
        "brooks_channel_line_valid": True,
        "brooks_channel_line_direction": "UP",
        "brooks_channel_line_slope": 1.0,
        "brooks_channel_line_width": 8.0,
        "brooks_channel_line_position": 0.5,
        "brooks_channel_line_level": 120.0,
        "brooks_channel_line_trend_level": 112.0,
        "brooks_channel_line_tested": False,
        "brooks_channel_line_returned_inside": False,
        "brooks_channel_line_accelerating": False,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def series(step=4.0):
    candles = []
    for index in range(7):
        center = 100 + index * step
        candles.append(candle(center - 2, center + 3, center - 3, center + 2))
    candles.append(candle(0, 1, -1, 0))
    return candles


def integrated(timeframe="M1", current=None):
    closed = (
        candle(102, 106, 100, 104),
        candle(104, 109, 105, 108),
        candle(106, 108, 102, 107),
        candle(107, 112, 108, 111),
        candle(108, 110, 104, 109),
        candle(109, 114, 110, 113),
        candle(110, 115, 106, 113),
    )
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for item in closed:
        market.candles.add(item)
    market.candles.add(current or candle(0, 1, -1, 0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = Trend.UP
    PriceAction().executar(context)
    return context.price_action


def teste_canal_apertado_se_comporta_como_tendencia():
    metrics = ChannelBehaviorDynamics.analyze(
        series(),
        source(brooks_channel_line_width=8.0),
    )
    assert metrics["brooks_channel_classification"] == "TIGHT"
    assert metrics["brooks_channel_behavior"] == "TREND_LIKE"
    assert metrics["brooks_channel_countertrend_risk"] is True


def teste_canal_amplo_se_comporta_como_faixa_inclinada():
    metrics = ChannelBehaviorDynamics.analyze(
        series(step=1.0),
        source(brooks_channel_line_width=30.0, brooks_channel_line_slope=0.2),
    )
    assert metrics["brooks_channel_classification"] == "WIDE"
    assert metrics["brooks_channel_behavior"] == "SLOPED_RANGE"
    assert metrics["brooks_channel_two_sided"] is True


def teste_posicao_e_dividida_em_tercos():
    low = ChannelBehaviorDynamics.analyze(series(), source(brooks_channel_line_position=0.2))
    middle = ChannelBehaviorDynamics.analyze(series(), source(brooks_channel_line_position=0.5))
    high = ChannelBehaviorDynamics.analyze(series(), source(brooks_channel_line_position=0.8))
    assert low["brooks_channel_location"] == "LOWER_THIRD"
    assert middle["brooks_channel_location"] == "MIDDLE"
    assert high["brooks_channel_location"] == "UPPER_THIRD"


def teste_retorno_ao_canal_mira_o_lado_oposto():
    metrics = ChannelBehaviorDynamics.analyze(
        series(),
        source(brooks_channel_line_returned_inside=True),
    )
    assert metrics["brooks_channel_state"] == "FAILED_BREAKOUT_RETURN"
    assert metrics["brooks_channel_measured_target"] == 112.0


def teste_rompimento_confirmado_projeta_movimento_medido():
    metrics = ChannelBehaviorDynamics.analyze(
        series(),
        source(brooks_channel_line_accelerating=True),
    )
    assert metrics["brooks_channel_state"] == "BREAKOUT_MEASURED_MOVE"
    assert metrics["brooks_channel_measured_target"] == 128.0


def teste_canal_de_baixa_projeta_alvo_simetrico():
    metrics = ChannelBehaviorDynamics.analyze(
        series(),
        source(
            brooks_channel_line_direction="DOWN",
            brooks_channel_line_level=90.0,
            brooks_channel_line_trend_level=98.0,
            brooks_channel_line_accelerating=True,
        ),
    )
    assert metrics["brooks_channel_direction"] == "DOWN"
    assert metrics["brooks_channel_measured_target"] == 82.0


def teste_sem_canal_valido_permanece_neutro():
    metrics = ChannelBehaviorDynamics.analyze(
        series(),
        source(brooks_channel_line_valid=False),
    )
    assert metrics["brooks_channel_state"] == "NO_CHANNEL"
    assert metrics["brooks_channel_valid"] is False


def teste_candle_atual_nao_contamina_o_comportamento():
    normal = integrated()
    extreme = integrated(current=candle(200, 500, 1, 2))
    assert normal.brooks_channel_state == extreme.brooks_channel_state
    assert normal.brooks_channel_classification == extreme.brooks_channel_classification


def teste_mesma_leitura_em_normal_e_renko():
    normal = integrated(timeframe="M1")
    renko = integrated(timeframe="RENKO_20")
    assert normal.brooks_channel_state == renko.brooks_channel_state
    assert normal.brooks_channel_behavior == renko.brooks_channel_behavior


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    result = integrated()
    before = (result.score, result.bias, result.bos, result.choch)
    ChannelBehaviorDynamics.analyze([], result)
    after = (result.score, result.bias, result.bos, result.choch)
    assert after == before


def teste_clear_remove_o_comportamento_anterior():
    result = integrated()
    result.clear()
    assert result.brooks_channel_state == "NO_CHANNEL"
    assert result.brooks_channel_classification == "NONE"
    assert result.brooks_channel_valid is False
    assert result.brooks_channel_third_push_risk is False


if __name__ == "__main__":
    tests = (
        teste_canal_apertado_se_comporta_como_tendencia,
        teste_canal_amplo_se_comporta_como_faixa_inclinada,
        teste_posicao_e_dividida_em_tercos,
        teste_retorno_ao_canal_mira_o_lado_oposto,
        teste_rompimento_confirmado_projeta_movimento_medido,
        teste_canal_de_baixa_projeta_alvo_simetrico,
        teste_sem_canal_valido_permanece_neutro,
        teste_candle_atual_nao_contamina_o_comportamento,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_o_comportamento_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 15 channel behavior")
