"""Testes do capítulo 14 de Trading Price Action Trends."""

from analysis.price_action.channel_line_dynamics import ChannelLineDynamics
from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


UP_BASE = (
    candle(102, 106, 100, 104),
    candle(104, 109, 105, 108),
    candle(106, 108, 102, 107),
    candle(107, 112, 108, 111),
    candle(108, 110, 104, 109),
    candle(109, 114, 110, 113),
)


DOWN_BASE = (
    candle(108, 110, 104, 106),
    candle(106, 105, 101, 102),
    candle(104, 108, 102, 103),
    candle(103, 102, 98, 99),
    candle(102, 106, 100, 101),
    candle(101, 100, 96, 97),
)


def analyze(closed, *, trend=Trend.UP, timeframe="M1", current=None):
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for item in closed:
        market.candles.add(item)
    market.candles.add(current or candle(0, 1, -1, 0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = trend
    PriceAction().executar(context)
    return context.price_action


def teste_canal_de_alta_cria_paralela_acima():
    result = analyze((*UP_BASE, candle(110, 115, 106, 113)))
    assert result.brooks_channel_line_valid is True
    assert result.brooks_channel_line_direction == "UP"
    assert result.brooks_channel_line_trend_level == 106
    assert result.brooks_channel_line_level == 115
    assert result.brooks_channel_line_width == 9


def teste_canal_de_baixa_cria_paralela_abaixo():
    result = analyze(
        (*DOWN_BASE, candle(99, 104, 95, 98)),
        trend=Trend.DOWN,
    )
    assert result.brooks_channel_line_valid is True
    assert result.brooks_channel_line_direction == "DOWN"
    assert result.brooks_channel_line_trend_level == 104
    assert result.brooks_channel_line_level == 95


def teste_preco_testa_linha_superior_do_canal():
    result = analyze((*UP_BASE, candle(110, 115, 106, 113)))
    assert result.brooks_channel_line_tested is True
    assert result.brooks_channel_line_state == "CHANNEL_LINE_TEST"


def teste_superacao_e_retorno_cria_candidato_de_reversao():
    result = analyze((*UP_BASE, candle(116, 118, 110, 114)))
    assert result.brooks_channel_line_overshoot is True
    assert result.brooks_channel_line_returned_inside is True
    assert result.brooks_channel_line_reversal_candidate is True
    assert result.brooks_channel_line_state == "OVERSHOOT_REVERSAL"


def teste_superacao_com_fechamento_fora_indica_aceleracao():
    result = analyze((*UP_BASE, candle(114, 119, 112, 118)))
    assert result.brooks_channel_line_overshoot is True
    assert result.brooks_channel_line_accelerating is True
    assert result.brooks_channel_line_state == "CHANNEL_BREAKOUT"


def teste_superacao_de_baixa_e_simetrica():
    result = analyze(
        (*DOWN_BASE, candle(96, 98, 92, 96)),
        trend=Trend.DOWN,
    )
    assert result.brooks_channel_line_overshoot is True
    assert result.brooks_channel_line_returned_inside is True
    assert result.brooks_channel_line_overshoot_distance == 3


def teste_sem_tendencia_clara_nao_cria_canal():
    result = analyze((*UP_BASE, candle(110, 115, 106, 113)), trend=Trend.SIDEWAYS)
    assert result.brooks_channel_line_state == "NO_CLEAR_TREND"
    assert result.brooks_channel_line_valid is False


def teste_candle_atual_nao_contamina_o_canal():
    closed = (*UP_BASE, candle(110, 115, 106, 113))
    normal = analyze(closed)
    extreme = analyze(closed, current=candle(200, 500, 1, 2))
    assert normal.brooks_channel_line_state == extreme.brooks_channel_line_state
    assert normal.brooks_channel_line_width == extreme.brooks_channel_line_width


def teste_mesma_leitura_em_normal_e_renko():
    closed = (*UP_BASE, candle(110, 115, 106, 113))
    normal = analyze(closed, timeframe="M1")
    renko = analyze(closed, timeframe="RENKO_20")
    assert normal.brooks_channel_line_state == renko.brooks_channel_line_state
    assert normal.brooks_channel_line_level == renko.brooks_channel_line_level


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    result = analyze((*UP_BASE, candle(110, 115, 106, 113)))
    before = (result.score, result.bias, result.bos, result.choch)
    ChannelLineDynamics.analyze([], trend=Trend.UP)
    after = (result.score, result.bias, result.bos, result.choch)
    assert after == before


def teste_clear_remove_o_canal_anterior():
    result = analyze((*UP_BASE, candle(110, 115, 106, 113)))
    result.clear()
    assert result.brooks_channel_line_state == "NO_CLEAR_TREND"
    assert result.brooks_channel_line_direction == "NONE"
    assert result.brooks_channel_line_valid is False
    assert result.brooks_channel_line_overshoot is False


if __name__ == "__main__":
    tests = (
        teste_canal_de_alta_cria_paralela_acima,
        teste_canal_de_baixa_cria_paralela_abaixo,
        teste_preco_testa_linha_superior_do_canal,
        teste_superacao_e_retorno_cria_candidato_de_reversao,
        teste_superacao_com_fechamento_fora_indica_aceleracao,
        teste_superacao_de_baixa_e_simetrica,
        teste_sem_tendencia_clara_nao_cria_canal,
        teste_candle_atual_nao_contamina_o_canal,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_o_canal_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 14 channel lines")
