"""Testes do capítulo 12 de Trading Price Action Trends."""

from types import SimpleNamespace

from analysis.price_action.pattern_evolution_dynamics import (
    PatternEvolutionDynamics,
)
from analysis.price_action.price_action import PriceAction
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def source(**changes):
    values = {
        "brooks_breakout_failed": False,
        "brooks_breakout_direction": "NONE",
        "brooks_failed_reversal": False,
        "brooks_failed_reversal_direction": "NONE",
        "brooks_outside_range_like": False,
        "brooks_ioi_pattern": False,
        "brooks_inside_sequence_count": 0,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def integrated(timeframe="M1", current=None):
    market = MarketState(symbol="WINV26", timeframe=timeframe)
    closed = (
        candle(100, 106, 98, 104),
        candle(104, 108, 102, 106),
        candle(106, 109, 104, 107),
        candle(107, 110, 105, 108),
        candle(108, 111, 106, 109),
    )
    for item in closed:
        market.candles.add(item)
    market.candles.add(current or candle(0, 1, -1, 0))
    context = AnalysisContext(market=market)
    context.structure.valid = True
    context.structure.trend = Trend.UP
    PriceAction().executar(context)
    return context.price_action


def teste_rompimento_de_alta_falha_e_evolui_para_reversao():
    metrics = PatternEvolutionDynamics.analyze(source(
        brooks_breakout_failed=True,
        brooks_breakout_direction="UP",
    ))
    assert metrics["brooks_evolution_pattern"] == "REVERSAL"
    assert metrics["brooks_evolution_direction"] == "DOWN"
    assert metrics["brooks_evolution_trapped_side"] == "BULLS"


def teste_rompimento_de_baixa_falha_e_simetrico():
    metrics = PatternEvolutionDynamics.analyze(source(
        brooks_breakout_failed=True,
        brooks_breakout_direction="DOWN",
    ))
    assert metrics["brooks_evolution_direction"] == "UP"
    assert metrics["brooks_evolution_trapped_side"] == "BEARS"


def teste_reversao_falha_e_evolui_para_continuacao():
    metrics = PatternEvolutionDynamics.analyze(source(
        brooks_failed_reversal=True,
        brooks_failed_reversal_direction="UP",
    ))
    assert metrics["brooks_evolution_state"] == "FAILED_REVERSAL_CONTINUATION"
    assert metrics["brooks_evolution_pattern"] == "TREND_CONTINUATION"
    assert metrics["brooks_evolution_confirmed"] is True


def teste_ioi_evolui_para_modo_de_rompimento():
    metrics = PatternEvolutionDynamics.analyze(source(
        brooks_ioi_pattern=True,
        brooks_inside_sequence_count=1,
    ))
    assert metrics["brooks_evolution_original_pattern"] == "IOI"
    assert metrics["brooks_evolution_breakout_mode"] is True
    assert metrics["brooks_evolution_direction"] == "BOTH"


def teste_sequencia_inside_amplia_com_tres_barras():
    metrics = PatternEvolutionDynamics.analyze(source(
        brooks_inside_sequence_count=3,
    ))
    assert metrics["brooks_evolution_pattern"] == "BREAKOUT_MODE"
    assert metrics["brooks_evolution_expanded"] is True


def teste_barra_externa_de_faixa_amplia_o_padrao():
    metrics = PatternEvolutionDynamics.analyze(source(
        brooks_outside_range_like=True,
    ))
    assert metrics["brooks_evolution_state"] == "EXPANDED_PATTERN"
    assert metrics["brooks_evolution_pattern"] == "EXPANDED_RANGE"
    assert metrics["brooks_evolution_breakout_mode"] is True


def teste_sem_evolucao_permanece_estavel():
    metrics = PatternEvolutionDynamics.analyze(source())
    assert metrics["brooks_evolution_state"] == "STABLE"
    assert metrics["brooks_evolution_pattern"] == "NONE"
    assert metrics["brooks_evolution_confirmed"] is False


def teste_candle_atual_nao_contamina_a_evolucao():
    normal = integrated()
    extreme = integrated(current=candle(200, 500, 1, 2))
    assert normal.brooks_evolution_state == extreme.brooks_evolution_state
    assert normal.brooks_evolution_pattern == extreme.brooks_evolution_pattern


def teste_mesma_leitura_em_normal_e_renko():
    normal = integrated(timeframe="M1")
    renko = integrated(timeframe="RENKO_20")
    assert normal.brooks_evolution_state == renko.brooks_evolution_state
    assert normal.brooks_evolution_direction == renko.brooks_evolution_direction


def teste_diagnostico_nao_altera_score_bias_bos_ou_choch():
    result = integrated()
    before = (result.score, result.bias, result.bos, result.choch)
    PatternEvolutionDynamics.analyze(result)
    after = (result.score, result.bias, result.bos, result.choch)
    assert after == before


def teste_clear_remove_a_evolucao_anterior():
    result = integrated()
    result.brooks_evolution_state = "FAILED_PATTERN_REVERSAL"
    result.brooks_evolution_confirmed = True
    result.clear()
    assert result.brooks_evolution_state == "STABLE"
    assert result.brooks_evolution_pattern == "NONE"
    assert result.brooks_evolution_confirmed is False


if __name__ == "__main__":
    tests = (
        teste_rompimento_de_alta_falha_e_evolui_para_reversao,
        teste_rompimento_de_baixa_falha_e_simetrico,
        teste_reversao_falha_e_evolui_para_continuacao,
        teste_ioi_evolui_para_modo_de_rompimento,
        teste_sequencia_inside_amplia_com_tres_barras,
        teste_barra_externa_de_faixa_amplia_o_padrao,
        teste_sem_evolucao_permanece_estavel,
        teste_candle_atual_nao_contamina_a_evolucao,
        teste_mesma_leitura_em_normal_e_renko,
        teste_diagnostico_nao_altera_score_bias_bos_ou_choch,
        teste_clear_remove_a_evolucao_anterior,
    )
    for test in tests:
        test()
    print("OK - Brooks Trends chapter 12 pattern evolution")
