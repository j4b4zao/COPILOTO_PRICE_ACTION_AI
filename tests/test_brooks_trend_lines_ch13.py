"""Testes do capítulo 13 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from analysis.price_action.trend_line_dynamics import TrendLineDynamics
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


def teste_linha_de_alta_liga_dois_fundos_ascendentes():
    result = analyze((*UP_BASE, candle(106, 112, 106, 110)))
    assert result.brooks_trend_line_valid is True
    assert result.brooks_trend_line_direction == "UP"
    assert result.brooks_trend_line_slope == 1.0
    assert result.brooks_trend_line_level == 106.0


def teste_linha_de_baixa_liga_dois_topos_descendentes():
    result = analyze(
        (*DOWN_BASE, candle(104, 104, 98, 100)),
        trend=Trend.DOWN,
    )
    assert result.brooks_trend_line_valid is True
    assert result.brooks_trend_line_direction == "DOWN"
    assert result.brooks_trend_line_slope == -1.0
    assert result.brooks_trend_line_level == 104.0


def teste_toque_com_rejeicao_preserva_a_linha():
    result = analyze((*UP_BASE, candle(106, 112, 105.8, 110)))
    assert result.brooks_trend_line_tested is True
    assert result.brooks_trend_line_rejected is True
    assert result.brooks_trend_line_state == "LINE_REJECTION"


def teste_fechamento_abaixo_rompe_linha_de_alta():
    result = analyze((*UP_BASE, candle(108, 109, 102, 103)))
    assert result.brooks_trend_line_broken is True
    assert result.brooks_trend_line_state == "LINE_BREAK"
    assert result.brooks_trend_line_two_sided_risk is True


def teste_fechamento_acima_rompe_linha_de_baixa():
    result = analyze(
        (*DOWN_BASE, candle(100, 109, 99, 108)),
        trend=Trend.DOWN,
    )
    assert result.brooks_trend_line_broken is True
    assert result.brooks_trend_line_break_strength > 0.0


def teste_sem_dois_swings_nao_cria_linha():
    monotonic = tuple(
        candle(100 + index, 103 + index, 99 + index, 102 + index)
        for index in range(7)
    )
    result = analyze(monotonic)
    assert result.brooks_trend_line_valid is False
    assert result.brooks_trend_line_state == "INSUFFICIENT_SWINGS"


def teste_sem_tendencia_clara_nao_cria_linha():
    result = analyze((*UP_BASE, candle(106, 112, 106, 110)), trend=Trend.SIDEWAYS)
    assert result.brooks_trend_line_state == "NO_CLEAR_TREND"
    assert result.brooks_trend_line_direction == "NONE"


def teste_candle_atual_nao_contamina_a_linha():
    closed = (*UP_BASE, candle(106, 112, 106, 110))
    normal = analyze(closed)
    extreme = analyze(closed, current=candle(200, 500, 1, 2))
    assert normal.brooks_trend_line_state == extreme.brooks_trend_line_state
    assert normal.brooks_trend_line_level == extreme.brooks_trend_line_level


def teste_mesma_leitura_em_normal_e_renko():
    closed = (*UP_BASE, candle(106, 112, 106, 110))
    normal = analyze(closed, timeframe="M1")
    renko = analyze(closed, timeframe="RENKO_20")
    assert normal.brooks_trend_line_state == renko.brooks_trend_line_state
    assert normal.brooks_trend_line_slope == renko.brooks_trend_line_slope


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    result = analyze((*UP_BASE, candle(106, 112, 106, 110)))
    before = (result.score, result.bias, result.bos, result.choch)
    TrendLineDynamics.analyze([], trend=Trend.UP)
    after = (result.score, result.bias, result.bos, result.choch)
    assert after == before


def teste_clear_remove_a_linha_anterior():
    result = analyze((*UP_BASE, candle(106, 112, 106, 110)))
    result.clear()
    assert result.brooks_trend_line_state == "NO_CLEAR_TREND"
    assert result.brooks_trend_line_direction == "NONE"
    assert result.brooks_trend_line_valid is False
    assert result.brooks_trend_line_broken is False


if __name__ == "__main__":
    tests = (
        teste_linha_de_alta_liga_dois_fundos_ascendentes,
        teste_linha_de_baixa_liga_dois_topos_descendentes,
        teste_toque_com_rejeicao_preserva_a_linha,
        teste_fechamento_abaixo_rompe_linha_de_alta,
        teste_fechamento_acima_rompe_linha_de_baixa,
        teste_sem_dois_swings_nao_cria_linha,
        teste_sem_tendencia_clara_nao_cria_linha,
        teste_candle_atual_nao_contamina_a_linha,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_a_linha_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 13 trend lines")
