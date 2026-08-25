"""Testes do Capítulo 5 de Trading Price Action Trends."""

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


REFERENCE = (
    candle(110.0, 111.0, 105.0, 106.0),
    candle(106.0, 107.0, 101.0, 102.0),
    candle(102.0, 103.0, 97.0, 98.0),
    candle(98.0, 99.0, 93.0, 94.0),
    candle(94.0, 95.0, 89.0, 90.0),
)


def analyze(closed, *, trend=Trend.DOWN, timeframe="M1", current=None):
    market = MarketState(symbol="WINV26", timeframe=timeframe)

    for item in closed:
        market.candles.add(item)

    market.candles.add(
        current or candle(0.0, 1.0, -1.0, 0.0)
    )

    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = trend
    PriceAction().executar(context)
    return context.price_action


def teste_barra_touro_forte_reverte_fechamentos_e_extremos():
    reversal = candle(89.0, 104.0, 84.0, 102.0)
    result = analyze((*REFERENCE, reversal))

    assert result.brooks_reversal_candidate is True
    assert result.brooks_reversal_direction == "BULL"
    assert result.brooks_reversal_quality == "STRONG"
    assert result.brooks_reversal_context == "COUNTER_TREND"
    assert result.brooks_reversal_reversed_closes >= 2
    assert result.brooks_reversal_reversed_extremes >= 2


def teste_barra_urso_forte_e_avaliada_simetricamente():
    rising = tuple(
        candle(item.close, item.high + 30.0, item.low + 30.0, item.open)
        for item in REFERENCE
    )
    reversal = candle(125.0, 130.0, 110.0, 112.0)
    result = analyze((*rising, reversal), trend=Trend.UP)

    assert result.brooks_reversal_candidate is True
    assert result.brooks_reversal_direction == "BEAR"
    assert result.brooks_reversal_context == "COUNTER_TREND"


def teste_sobreposicao_excessiva_reduz_qualidade():
    reference = (
        candle(100.0, 110.0, 90.0, 92.0),
        candle(102.0, 111.0, 91.0, 93.0),
        candle(101.0, 109.0, 89.0, 92.0),
        candle(100.0, 110.0, 90.0, 91.0),
        candle(99.0, 109.0, 89.0, 90.0),
    )
    reversal = candle(90.0, 110.0, 88.0, 106.0)
    result = analyze((*reference, reversal))

    assert result.brooks_reversal_candidate is True
    assert result.brooks_reversal_excessive_overlap is True
    assert result.brooks_reversal_quality != "STRONG"


def teste_grande_doji_e_marcado_como_risco_e_rejeitado():
    reversal = candle(90.0, 105.0, 75.0, 91.0)
    result = analyze((*REFERENCE, reversal))

    assert result.brooks_reversal_candidate is True
    assert result.brooks_reversal_large_doji_risk is True
    assert result.brooks_reversal_quality == "REJECTED"


def teste_barra_comum_sem_evidencia_nao_vira_reversao():
    sideways = (
        candle(100.0, 104.0, 98.0, 102.0),
        candle(102.0, 106.0, 100.0, 104.0),
        candle(104.0, 108.0, 102.0, 106.0),
        candle(106.0, 110.0, 104.0, 108.0),
        candle(108.0, 112.0, 106.0, 110.0),
    )
    continuation = candle(110.0, 114.0, 109.0, 113.0)
    result = analyze((*sideways, continuation), trend=Trend.UP)

    assert result.brooks_reversal_candidate is False
    assert result.brooks_reversal_direction == "NONE"
    assert result.brooks_reversal_quality == "NONE"


def teste_candle_atual_nao_contamina_a_barra_fechada():
    closed = (*REFERENCE, candle(89.0, 104.0, 84.0, 102.0))
    normal = analyze(closed)
    extreme = analyze(
        closed,
        current=candle(102.0, 300.0, 10.0, 20.0),
    )

    assert normal.brooks_reversal_quality == extreme.brooks_reversal_quality
    assert normal.brooks_reversal_direction == extreme.brooks_reversal_direction


def teste_mesma_leitura_em_normal_e_renko():
    closed = (*REFERENCE, candle(89.0, 104.0, 84.0, 102.0))
    normal = analyze(closed, timeframe="M1")
    renko = analyze(closed, timeframe="RENKO_20")

    assert normal.brooks_reversal_quality == renko.brooks_reversal_quality
    assert normal.brooks_reversal_direction == renko.brooks_reversal_direction
    assert normal.brooks_reversal_tail_ratio == renko.brooks_reversal_tail_ratio


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    baseline = analyze(REFERENCE)
    reversal = analyze((*REFERENCE, candle(89.0, 104.0, 84.0, 102.0)))

    assert baseline.score == reversal.score
    assert baseline.bias == reversal.bias == "SELL"
    assert baseline.bos is reversal.bos is False
    assert baseline.choch is reversal.choch is False


def teste_clear_remove_metricas_da_reversao_anterior():
    result = analyze((*REFERENCE, candle(89.0, 104.0, 84.0, 102.0)))

    result.clear()

    assert result.brooks_reversal_candidate is False
    assert result.brooks_reversal_direction == "NONE"
    assert result.brooks_reversal_quality == "NONE"
    assert result.brooks_reversal_reversed_closes == 0
    assert result.brooks_reversal_large_doji_risk is False


if __name__ == "__main__":
    tests = (
        teste_barra_touro_forte_reverte_fechamentos_e_extremos,
        teste_barra_urso_forte_e_avaliada_simetricamente,
        teste_sobreposicao_excessiva_reduz_qualidade,
        teste_grande_doji_e_marcado_como_risco_e_rejeitado,
        teste_barra_comum_sem_evidencia_nao_vira_reversao,
        teste_candle_atual_nao_contamina_a_barra_fechada,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_metricas_da_reversao_anterior,
    )

    for test in tests:
        test()

    print("OK - Brooks Trends chapter 5 reversal bar quality")
