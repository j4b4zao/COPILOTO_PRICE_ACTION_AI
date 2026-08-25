"""Testes do Capítulo 4 de Trading Price Action Trends."""

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


def analyze(closed, *, trend=Trend.UP, timeframe="M1", current=None):
    market = MarketState(
        symbol="WINV26",
        timeframe=timeframe,
    )

    warmup = (
        candle(97.0, 100.0, 96.0, 99.0),
        candle(99.0, 102.0, 98.0, 100.0),
        candle(100.0, 110.0, 90.0, 101.0),
    )

    for item in (*warmup, *closed):
        market.candles.add(item)

    market.candles.add(
        current or candle(0.0, 1.0, -1.0, 0.0)
    )

    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = trend
    PriceAction().executar(context)
    return context.price_action


def teste_ultima_barra_fechada_e_configuracao_pendente():
    result = analyze(
        (
            candle(100.0, 105.0, 98.0, 102.0),
            candle(100.0, 104.0, 99.0, 103.0),
        )
    )

    assert result.brooks_signal_phase == "SETUP_PENDING"
    assert result.brooks_signal_direction == "UP"
    assert result.brooks_entry_level == 104.0
    assert result.brooks_entry_triggered is False


def teste_fuga_da_maxima_transforma_configuracao_em_sinal():
    signal = candle(100.0, 104.0, 99.0, 103.0)
    entry = candle(103.0, 107.0, 102.0, 106.0)
    result = analyze((signal, entry))

    assert result.brooks_signal_phase == "ENTRY_TRIGGERED"
    assert result.brooks_signal_direction == "UP"
    assert result.brooks_entry_level == 104.0
    assert result.brooks_entry_triggered is True
    assert result.brooks_signal_quality == "STRONG"
    assert result.brooks_signal_context == "WITH_TREND"


def teste_segunda_barra_direcional_confirma_follow_through():
    signal = candle(100.0, 104.0, 99.0, 103.0)
    entry = candle(103.0, 107.0, 102.0, 106.0)
    follow = candle(106.0, 111.0, 105.0, 110.0)
    result = analyze((signal, entry, follow))

    assert result.brooks_signal_phase == "FOLLOW_THROUGH"
    assert result.brooks_follow_through is True
    assert result.brooks_follow_through_strength == "STRONG"


def teste_entrada_sem_continuacao_fica_estagnada():
    signal = candle(100.0, 104.0, 99.0, 103.0)
    entry = candle(103.0, 107.0, 102.0, 106.0)
    pause = candle(106.0, 107.0, 103.0, 104.0)
    result = analyze((signal, entry, pause))

    assert result.brooks_signal_phase == "ENTRY_STALLED"
    assert result.brooks_entry_triggered is True
    assert result.brooks_follow_through is False
    assert result.brooks_follow_through_strength == "NONE"


def teste_entrada_de_baixa_contra_tendencia_e_identificada():
    signal = candle(103.0, 104.0, 99.0, 100.0)
    entry = candle(100.0, 101.0, 96.0, 97.0)
    result = analyze((signal, entry), trend=Trend.UP)

    assert result.brooks_signal_direction == "DOWN"
    assert result.brooks_signal_context == "COUNTER_TREND"
    assert result.brooks_entry_level == 99.0


def teste_doji_tem_qualidade_fraca_sem_bloquear_diagnostico():
    signal = candle(100.0, 105.0, 95.0, 100.5)
    entry = candle(100.5, 107.0, 100.0, 106.0)
    result = analyze((signal, entry))

    assert result.brooks_signal_phase == "ENTRY_TRIGGERED"
    assert result.brooks_signal_quality == "WEAK"


def teste_candle_atual_nao_contamina_o_ciclo():
    closed = (
        candle(100.0, 104.0, 99.0, 103.0),
        candle(103.0, 107.0, 102.0, 106.0),
        candle(106.0, 111.0, 105.0, 110.0),
    )
    normal = analyze(closed)
    extreme = analyze(
        closed,
        current=candle(110.0, 300.0, 10.0, 20.0),
    )

    assert normal.brooks_signal_phase == extreme.brooks_signal_phase
    assert normal.brooks_entry_level == extreme.brooks_entry_level


def teste_mesma_leitura_ohlc_em_normal_e_renko():
    closed = (
        candle(100.0, 104.0, 99.0, 103.0),
        candle(103.0, 107.0, 102.0, 106.0),
        candle(106.0, 111.0, 105.0, 110.0),
    )
    normal = analyze(closed, timeframe="M1")
    renko = analyze(closed, timeframe="RENKO_20")

    assert normal.brooks_signal_phase == renko.brooks_signal_phase
    assert normal.brooks_signal_quality == renko.brooks_signal_quality
    assert normal.brooks_follow_through == renko.brooks_follow_through


def teste_ciclo_informativo_nao_altera_score_bias_ou_bos():
    pending = analyze(
        (
            candle(100.0, 105.0, 98.0, 102.0),
            candle(100.0, 104.0, 99.0, 103.0),
        )
    )
    followed = analyze(
        (
            candle(100.0, 104.0, 99.0, 103.0),
            candle(103.0, 107.0, 102.0, 106.0),
            candle(106.0, 111.0, 105.0, 110.0),
        )
    )

    assert pending.score == followed.score
    assert pending.bias == followed.bias == "BUY"
    assert pending.bos is followed.bos is False


def teste_clear_remove_estado_do_ciclo_anterior():
    result = analyze(
        (
            candle(100.0, 104.0, 99.0, 103.0),
            candle(103.0, 107.0, 102.0, 106.0),
            candle(106.0, 111.0, 105.0, 110.0),
        )
    )

    result.clear()

    assert result.brooks_signal_phase == "UNKNOWN"
    assert result.brooks_signal_direction == "NONE"
    assert result.brooks_signal_quality == "UNKNOWN"
    assert result.brooks_entry_level == 0.0
    assert result.brooks_entry_triggered is False
    assert result.brooks_follow_through is False


if __name__ == "__main__":
    tests = (
        teste_ultima_barra_fechada_e_configuracao_pendente,
        teste_fuga_da_maxima_transforma_configuracao_em_sinal,
        teste_segunda_barra_direcional_confirma_follow_through,
        teste_entrada_sem_continuacao_fica_estagnada,
        teste_entrada_de_baixa_contra_tendencia_e_identificada,
        teste_doji_tem_qualidade_fraca_sem_bloquear_diagnostico,
        teste_candle_atual_nao_contamina_o_ciclo,
        teste_mesma_leitura_ohlc_em_normal_e_renko,
        teste_ciclo_informativo_nao_altera_score_bias_ou_bos,
        teste_clear_remove_estado_do_ciclo_anterior,
    )

    for test in tests:
        test()

    print("OK - Brooks Trends chapter 4 signal/entry cycle")
