"""Testes do capítulo 9 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(close):
    return Candle(
        open=close - 1.0,
        high=close + 2.0,
        low=close - 2.0,
        close=close,
        volume=1000.0,
    )


def analyze(closes, *, timeframe="M1", current=999.0):
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for close in closes:
        market.candles.add(candle(close))
    market.candles.add(candle(current))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = Trend.UP
    PriceAction().executar(context)
    return context.price_action


def teste_perspectiva_de_alta_forte_e_confirmada():
    result = analyze((100, 102, 104, 106, 108, 110))
    assert result.brooks_perspective_direction == "UP"
    assert result.brooks_perspective_inverse_direction == "DOWN"
    assert result.brooks_perspective_clarity == "STRONG"
    assert result.brooks_perspective_confirmed is True


def teste_perspectiva_de_baixa_forte_e_simetrica():
    result = analyze((110, 108, 106, 104, 102, 100))
    assert result.brooks_perspective_direction == "DOWN"
    assert result.brooks_perspective_inverse_direction == "UP"
    assert result.brooks_perspective_inverse_consistent is True


def teste_movimento_ruidoso_permanece_ambiguo():
    result = analyze((100, 105, 99, 104, 98, 101))
    assert result.brooks_perspective_clarity == "AMBIGUOUS"
    assert result.brooks_perspective_confirmed is False


def teste_fechamentos_planos_sao_neutros():
    result = analyze((100, 100, 100, 100, 100, 100))
    assert result.brooks_perspective_direction == "NEUTRAL"
    assert result.brooks_perspective_state == "AMBIGUOUS_PERSPECTIVE"


def teste_eficiencia_mede_progresso_sobre_percurso():
    clean = analyze((100, 102, 104, 106, 108, 110))
    noisy = analyze((100, 104, 102, 106, 104, 110))
    assert clean.brooks_perspective_efficiency == 1.0
    assert noisy.brooks_perspective_efficiency < 1.0


def teste_consistencia_conta_passos_alinhados():
    result = analyze((100, 102, 104, 103, 106, 108))
    assert result.brooks_perspective_consistency == 0.8


def teste_candle_atual_nao_contamina_a_perspectiva():
    normal = analyze((100, 102, 104, 106, 108, 110), current=111)
    extreme = analyze((100, 102, 104, 106, 108, 110), current=1)
    assert normal.brooks_perspective_state == extreme.brooks_perspective_state
    assert normal.brooks_perspective_efficiency == extreme.brooks_perspective_efficiency


def teste_mesma_leitura_em_normal_e_renko():
    closes = (100, 102, 104, 106, 108, 110)
    normal = analyze(closes, timeframe="M1")
    renko = analyze(closes, timeframe="RENKO_20")
    assert normal.brooks_perspective_state == renko.brooks_perspective_state
    assert normal.brooks_perspective_clarity == renko.brooks_perspective_clarity


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    strong = analyze((100, 102, 104, 106, 108, 110))
    noisy = analyze((100, 105, 99, 104, 98, 101))
    assert strong.score == noisy.score
    assert strong.bias == noisy.bias == "BUY"
    assert strong.bos is noisy.bos is False
    assert strong.choch is noisy.choch is False


def teste_clear_remove_a_perspectiva_anterior():
    result = analyze((100, 102, 104, 106, 108, 110))
    result.clear()
    assert result.brooks_perspective_state == "UNKNOWN"
    assert result.brooks_perspective_direction == "NEUTRAL"
    assert result.brooks_perspective_clarity == "UNKNOWN"
    assert result.brooks_perspective_confirmed is False


if __name__ == "__main__":
    tests = (
        teste_perspectiva_de_alta_forte_e_confirmada,
        teste_perspectiva_de_baixa_forte_e_simetrica,
        teste_movimento_ruidoso_permanece_ambiguo,
        teste_fechamentos_planos_sao_neutros,
        teste_eficiencia_mede_progresso_sobre_percurso,
        teste_consistencia_conta_passos_alinhados,
        teste_candle_atual_nao_contamina_a_perspectiva,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_a_perspectiva_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 9 chart perspective")
