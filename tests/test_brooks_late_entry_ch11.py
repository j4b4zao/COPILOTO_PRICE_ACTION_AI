"""Testes do capítulo 11 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


BASE = (
    candle(100, 102, 98, 100),
    candle(100, 102, 98, 100),
)


UP_LEG = (
    candle(101, 104, 100, 103),
    candle(103, 106, 102, 105),
    candle(105, 108, 104, 107),
    candle(107, 110, 106, 109),
)


DOWN_LEG = (
    candle(109, 110, 106, 107),
    candle(107, 108, 104, 105),
    candle(105, 106, 102, 103),
    candle(103, 104, 100, 101),
)


def analyze(closed, *, trend=Trend.UP, timeframe="M1", current=None):
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for item in (*BASE, *closed):
        market.candles.add(item)
    market.candles.add(current or candle(0, 1, -1, 0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = trend
    PriceAction().executar(context)
    return context.price_action


def teste_entrada_tardia_de_compra_em_tendencia_clara():
    result = analyze(UP_LEG)
    assert result.brooks_late_entry_direction == "BUY"
    assert result.brooks_late_entry_trend_bars == 4
    assert result.brooks_late_entry_state == "LATE_ENTRY_CANDIDATE"
    assert result.brooks_late_entry_confirmed is True


def teste_entrada_tardia_de_venda_e_simetrica():
    result = analyze(DOWN_LEG, trend=Trend.DOWN)
    assert result.brooks_late_entry_direction == "SELL"
    assert result.brooks_late_entry_missed is True
    assert result.brooks_late_entry_candidate is True


def teste_candidato_exige_reducao_de_posicao():
    result = analyze(UP_LEG)
    assert result.brooks_late_entry_reduce_position is True
    assert result.brooks_late_entry_stop_reference == 100
    assert result.brooks_late_entry_stop_distance == 9


def teste_menos_de_quatro_barras_nao_e_entrada_perdida():
    result = analyze(UP_LEG[:3])
    assert result.brooks_late_entry_missed is False
    assert result.brooks_late_entry_candidate is False
    assert result.brooks_late_entry_state == "NO_LATE_ENTRY"


def teste_pullback_apos_perna_forte_e_identificado():
    pullback = candle(109, 110, 106, 107)
    result = analyze((*UP_LEG, pullback))
    assert result.brooks_late_entry_pullback_available is True
    assert result.brooks_late_entry_state == "PULLBACK_AVAILABLE"


def teste_climax_extenso_bloqueia_perseguicao():
    long_leg = tuple(
        candle(100 + index * 2, 103 + index * 2, 99 + index * 2, 102 + index * 2)
        for index in range(8)
    )
    result = analyze(long_leg)
    assert result.brooks_late_entry_climax_risk is True
    assert result.brooks_late_entry_state == "AVOID_CHASING"
    assert result.brooks_late_entry_candidate is False


def teste_sem_tendencia_clara_nao_cria_candidato():
    result = analyze(UP_LEG, trend=Trend.SIDEWAYS)
    assert result.brooks_late_entry_state == "NO_CLEAR_TREND"
    assert result.brooks_late_entry_direction == "NONE"


def teste_candle_atual_nao_contamina_a_entrada_tardia():
    normal = analyze(UP_LEG)
    extreme = analyze(UP_LEG, current=candle(200, 500, 1, 2))
    assert normal.brooks_late_entry_state == extreme.brooks_late_entry_state
    assert normal.brooks_late_entry_stop_reference == extreme.brooks_late_entry_stop_reference


def teste_mesma_leitura_em_normal_e_renko():
    normal = analyze(UP_LEG, timeframe="M1")
    renko = analyze(UP_LEG, timeframe="RENKO_20")
    assert normal.brooks_late_entry_state == renko.brooks_late_entry_state
    assert normal.brooks_late_entry_efficiency == renko.brooks_late_entry_efficiency


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    late = analyze(UP_LEG)
    early = analyze(UP_LEG[:3])
    assert late.score == early.score
    assert late.bias == early.bias == "BUY"
    assert late.bos is early.bos is False
    assert late.choch is early.choch is False


def teste_clear_remove_a_entrada_tardia_anterior():
    result = analyze(UP_LEG)
    result.clear()
    assert result.brooks_late_entry_state == "NO_CLEAR_TREND"
    assert result.brooks_late_entry_direction == "NONE"
    assert result.brooks_late_entry_candidate is False
    assert result.brooks_late_entry_confirmed is False


if __name__ == "__main__":
    tests = (
        teste_entrada_tardia_de_compra_em_tendencia_clara,
        teste_entrada_tardia_de_venda_e_simetrica,
        teste_candidato_exige_reducao_de_posicao,
        teste_menos_de_quatro_barras_nao_e_entrada_perdida,
        teste_pullback_apos_perna_forte_e_identificado,
        teste_climax_extenso_bloqueia_perseguicao,
        teste_sem_tendencia_clara_nao_cria_candidato,
        teste_candle_atual_nao_contamina_a_entrada_tardia,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_a_entrada_tardia_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 11 late entry")
