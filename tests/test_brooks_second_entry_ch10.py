"""Testes do capítulo 10 de Trading Price Action Trends."""

from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


WARMUP = (
    candle(100, 103, 99, 102),
    candle(102, 105, 101, 104),
    candle(104, 107, 103, 106),
    candle(106, 109, 105, 108),
)


def analyze(closed, *, trend=Trend.UP, timeframe="M1", current=None):
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    for item in (*WARMUP, *closed):
        market.candles.add(item)
    market.candles.add(current or candle(0, 1, -1, 0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = trend
    PriceAction().executar(context)
    return context.price_action


def buy_pattern(second_high=114):
    return (
        candle(108, 109, 104, 105),
        candle(105, 112, 104, 111),
        candle(111, 112, 106, 107),
        candle(107, second_high, 106, second_high - 1),
    )


def sell_pattern(second_low=96):
    return (
        candle(100, 105, 99, 104),
        candle(104, 105, 98, 99),
        candle(99, 103, 98, 102),
        candle(102, 103, second_low, second_low + 1),
    )


def teste_segunda_entrada_de_compra_com_tendencia():
    result = analyze(buy_pattern())
    assert result.brooks_second_entry_detected is True
    assert result.brooks_second_entry_direction == "BUY"
    assert result.brooks_second_entry_context == "WITH_TREND"
    assert result.brooks_second_entry_quality == "STRONG"


def teste_segunda_entrada_de_venda_com_tendencia():
    result = analyze(sell_pattern(), trend=Trend.DOWN)
    assert result.brooks_second_entry_detected is True
    assert result.brooks_second_entry_direction == "SELL"
    assert result.brooks_second_entry_context == "WITH_TREND"


def teste_preco_pior_ou_igual_e_comportamento_esperado():
    result = analyze(buy_pattern(second_high=114))
    assert result.brooks_second_entry_price_relation == "WORSE_EXPECTED"
    assert result.brooks_second_entry_bargain_risk is False
    assert result.brooks_second_entry_confirmed is True


def teste_preco_melhor_marca_pechincha_suspeita():
    result = analyze(buy_pattern(second_high=110))
    assert result.brooks_second_entry_price_relation == "BETTER_SUSPICIOUS"
    assert result.brooks_second_entry_bargain_risk is True
    assert result.brooks_second_entry_quality == "CAUTION"
    assert result.brooks_second_entry_confirmed is False


def teste_uma_unica_tentativa_nao_e_segunda_entrada():
    result = analyze(buy_pattern()[:2])
    assert result.brooks_second_entry_detected is False
    assert result.brooks_second_entry_direction == "BUY"
    assert result.brooks_second_entry_phase == "FIRST_ENTRY"


def teste_entrada_contra_tendencia_recebe_contexto_correto():
    result = analyze(sell_pattern(), trend=Trend.UP)
    assert result.brooks_second_entry_context == "COUNTER_TREND"
    assert result.brooks_second_entry_opposing_momentum is True
    assert result.brooks_second_entry_quality == "CAUTION"


def teste_candle_atual_nao_contamina_a_segunda_entrada():
    normal = analyze(buy_pattern())
    extreme = analyze(
        buy_pattern(),
        current=candle(200, 500, 1, 2),
    )
    assert normal.brooks_second_entry_phase == extreme.brooks_second_entry_phase
    assert normal.brooks_second_entry_level == extreme.brooks_second_entry_level


def teste_mesma_leitura_em_normal_e_renko():
    normal = analyze(buy_pattern(), timeframe="M1")
    renko = analyze(buy_pattern(), timeframe="RENKO_20")
    assert normal.brooks_second_entry_phase == renko.brooks_second_entry_phase
    assert normal.brooks_second_entry_quality == renko.brooks_second_entry_quality


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    second = analyze(buy_pattern())
    first = analyze(buy_pattern()[:2])
    assert second.score == first.score
    assert second.bias == first.bias == "BUY"
    assert second.bos is first.bos is False
    assert second.choch is first.choch is False


def teste_clear_remove_a_segunda_entrada_anterior():
    result = analyze(buy_pattern())
    result.clear()
    assert result.brooks_second_entry_phase == "NONE"
    assert result.brooks_second_entry_direction == "NONE"
    assert result.brooks_second_entry_attempt_count == 0
    assert result.brooks_second_entry_detected is False
    assert result.brooks_second_entry_confirmed is False


if __name__ == "__main__":
    tests = (
        teste_segunda_entrada_de_compra_com_tendencia,
        teste_segunda_entrada_de_venda_com_tendencia,
        teste_preco_pior_ou_igual_e_comportamento_esperado,
        teste_preco_melhor_marca_pechincha_suspeita,
        teste_uma_unica_tentativa_nao_e_segunda_entrada,
        teste_entrada_contra_tendencia_recebe_contexto_correto,
        teste_candle_atual_nao_contamina_a_segunda_entrada,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_a_segunda_entrada_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 10 second entry")
