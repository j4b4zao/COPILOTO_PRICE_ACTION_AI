"""Testes do Capítulo 3 de Trading Price Action Trends."""

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


BASE = (
    candle(100.0, 105.0, 95.0, 102.0),
    candle(102.0, 106.0, 96.0, 100.0),
    candle(100.0, 104.0, 94.0, 101.0),
    candle(101.0, 105.0, 95.0, 99.0),
    candle(99.0, 103.0, 93.0, 100.0),
)


def analyze(closed, current=None):
    market = MarketState(
        symbol="WINV26",
        timeframe="M1",
    )

    for item in closed:
        market.candles.add(item)

    market.candles.add(
        current or candle(0.0, 1.0, -1.0, 0.0)
    )

    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = Trend.UP
    PriceAction().executar(context)
    return context.price_action


def teste_range_expoe_limites_sem_criar_rompimento():
    result = analyze(BASE)

    assert result.brooks_breakout_phase == "RANGE"
    assert result.brooks_breakout_direction == "NONE"
    assert result.brooks_range_high == 106.0
    assert result.brooks_range_low == 93.0
    assert result.brooks_breakout_follow_through is False
    assert result.brooks_breakout_failed is False


def teste_novo_rompimento_de_alta_fica_pendente():
    result = analyze(
        (*BASE, candle(100.0, 110.0, 99.0, 108.0))
    )

    assert result.brooks_breakout_phase == "BREAKOUT_PENDING"
    assert result.brooks_breakout_direction == "UP"
    assert result.brooks_breakout_level == 106.0
    assert result.brooks_breakout_penetration == 2.0


def teste_follow_through_confirma_rompimento_de_alta():
    breakout = candle(100.0, 110.0, 99.0, 108.0)
    confirmation = candle(108.0, 113.0, 107.0, 112.0)
    result = analyze((*BASE, breakout, confirmation))

    assert result.brooks_breakout_phase == "BREAKOUT_CONFIRMED"
    assert result.brooks_breakout_direction == "UP"
    assert result.brooks_breakout_follow_through is True
    assert result.brooks_breakout_distance == 6.0


def teste_reteste_mantendo_nivel_classifica_tested():
    breakout = candle(100.0, 110.0, 99.0, 108.0)
    retest = candle(108.0, 109.0, 105.0, 107.0)
    result = analyze((*BASE, breakout, retest))

    assert result.brooks_breakout_phase == "BREAKOUT_TESTED"
    assert result.brooks_breakout_tested is True
    assert result.brooks_breakout_failed is False
    assert result.brooks_breakout_distance == 1.0


def teste_fechamento_dentro_do_range_falha_rompimento():
    breakout = candle(100.0, 110.0, 99.0, 108.0)
    failure = candle(108.0, 109.0, 101.0, 104.0)
    result = analyze((*BASE, breakout, failure))

    assert result.brooks_breakout_phase == "BREAKOUT_FAILED"
    assert result.brooks_breakout_failed is True
    assert result.brooks_breakout_follow_through is False
    assert result.brooks_breakout_distance == -2.0


def teste_rompimento_de_baixa_e_confirmacao():
    breakout = candle(100.0, 101.0, 89.0, 91.0)
    confirmation = candle(91.0, 92.0, 85.0, 87.0)
    result = analyze((*BASE, breakout, confirmation))

    assert result.brooks_breakout_phase == "BREAKOUT_CONFIRMED"
    assert result.brooks_breakout_direction == "DOWN"
    assert result.brooks_breakout_level == 93.0
    assert result.brooks_breakout_follow_through is True


def teste_candle_atual_nao_contamina_ciclo():
    closed = (
        *BASE,
        candle(100.0, 110.0, 99.0, 108.0),
        candle(108.0, 113.0, 107.0, 112.0),
    )
    normal = analyze(closed)
    extreme = analyze(
        closed,
        current=candle(112.0, 300.0, 10.0, 20.0),
    )

    assert (
        normal.brooks_breakout_phase
        == extreme.brooks_breakout_phase
    )
    assert (
        normal.brooks_breakout_distance
        == extreme.brooks_breakout_distance
    )


def teste_ciclo_nao_altera_score_ou_bos():
    baseline = analyze(BASE)
    breakout = analyze(
        (*BASE, candle(100.0, 110.0, 99.0, 108.0))
    )

    assert baseline.score == breakout.score
    assert baseline.breakout is False
    assert breakout.breakout is False
    assert baseline.bias == breakout.bias == "BUY"


if __name__ == "__main__":
    tests = (
        teste_range_expoe_limites_sem_criar_rompimento,
        teste_novo_rompimento_de_alta_fica_pendente,
        teste_follow_through_confirma_rompimento_de_alta,
        teste_reteste_mantendo_nivel_classifica_tested,
        teste_fechamento_dentro_do_range_falha_rompimento,
        teste_rompimento_de_baixa_e_confirmacao,
        teste_candle_atual_nao_contamina_ciclo,
        teste_ciclo_nao_altera_score_ou_bos,
    )

    for test in tests:
        test()

    print("OK - Brooks Trends chapter 3 breakout lifecycle")
