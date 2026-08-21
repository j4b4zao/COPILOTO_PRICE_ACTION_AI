"""Testes do Capítulo 8 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


WARMUP = (
    candle(100.0, 106.0, 98.0, 104.0),
    candle(104.0, 110.0, 102.0, 108.0),
    candle(108.0, 114.0, 106.0, 112.0),
    candle(112.0, 118.0, 110.0, 116.0),
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


def teste_fechamento_forte_de_alta_proximo_da_maxima():
    result = analyze((candle(116.0, 125.0, 114.0, 124.0),))
    assert result.brooks_close_direction == "UP"
    assert result.brooks_close_quality == "STRONG"
    assert result.brooks_close_near_extreme is True
    assert result.brooks_close_confirmed is True
    assert result.brooks_close_context == "WITH_TREND"


def teste_fechamento_forte_de_baixa_e_simetrico():
    result = analyze(
        (candle(116.0, 118.0, 106.0, 107.0),),
        trend=Trend.DOWN,
    )
    assert result.brooks_close_direction == "DOWN"
    assert result.brooks_close_quality == "STRONG"
    assert result.brooks_close_context == "WITH_TREND"


def teste_fechamento_no_meio_permanece_neutro():
    result = analyze((candle(116.0, 126.0, 106.0, 116.0),))
    assert result.brooks_close_direction == "NEUTRAL"
    assert result.brooks_close_quality == "MID_RANGE"
    assert result.brooks_close_confirmed is False
    assert result.brooks_close_state == "MID_RANGE_CLOSE"


def teste_follow_through_exige_dois_fechamentos_fortes():
    result = analyze((
        candle(116.0, 124.0, 114.0, 123.0),
        candle(123.0, 130.0, 121.0, 129.0),
    ))
    assert result.brooks_close_follow_through is True
    assert result.brooks_close_consistency >= 2
    assert result.brooks_close_progress > 0.0


def teste_deterioracao_apos_fechamento_forte():
    result = analyze((
        candle(116.0, 124.0, 114.0, 123.0),
        candle(123.0, 125.0, 116.0, 119.0),
    ))
    assert result.brooks_close_deterioration is True
    assert result.brooks_close_follow_through is False


def teste_fechamento_reverte_varios_fechamentos_anteriores():
    result = analyze((candle(116.0, 130.0, 114.0, 129.0),))
    assert result.brooks_close_reversed_closes >= 3


def teste_candle_atual_nao_contamina_o_fechamento_confirmado():
    closed = (candle(116.0, 125.0, 114.0, 124.0),)
    normal = analyze(closed)
    extreme = analyze(
        closed,
        current=candle(124.0, 300.0, 10.0, 20.0),
    )
    assert normal.brooks_close_state == extreme.brooks_close_state
    assert normal.brooks_close_position == extreme.brooks_close_position


def teste_mesma_leitura_em_normal_e_renko():
    closed = (
        candle(116.0, 124.0, 114.0, 123.0),
        candle(123.0, 130.0, 121.0, 129.0),
    )
    normal = analyze(closed, timeframe="M1")
    renko = analyze(closed, timeframe="RENKO_20")
    assert normal.brooks_close_quality == renko.brooks_close_quality
    assert normal.brooks_close_consistency == renko.brooks_close_consistency


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    neutral = analyze((candle(116.0, 126.0, 106.0, 116.0),))
    strong = analyze((candle(116.0, 125.0, 114.0, 124.0),))
    assert neutral.score == strong.score
    assert neutral.bias == strong.bias == "BUY"
    assert neutral.bos is strong.bos is False
    assert neutral.choch is strong.choch is False


def teste_clear_remove_qualidade_do_fechamento_anterior():
    result = analyze((candle(116.0, 125.0, 114.0, 124.0),))
    result.clear()
    assert result.brooks_close_state == "UNKNOWN"
    assert result.brooks_close_direction == "NEUTRAL"
    assert result.brooks_close_quality == "UNKNOWN"
    assert result.brooks_close_confirmed is False
    assert result.brooks_close_deterioration is False


if __name__ == "__main__":
    tests = (
        teste_fechamento_forte_de_alta_proximo_da_maxima,
        teste_fechamento_forte_de_baixa_e_simetrico,
        teste_fechamento_no_meio_permanece_neutro,
        teste_follow_through_exige_dois_fechamentos_fortes,
        teste_deterioracao_apos_fechamento_forte,
        teste_fechamento_reverte_varios_fechamentos_anteriores,
        teste_candle_atual_nao_contamina_o_fechamento_confirmado,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_qualidade_do_fechamento_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 8 close quality")
